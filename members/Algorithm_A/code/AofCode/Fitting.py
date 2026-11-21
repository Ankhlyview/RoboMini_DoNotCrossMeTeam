from __future__ import annotations

import os
import math
import time 
import cv2
import numpy as np

import detect 
import geometry

# 所有要用到的东西，到时候那个没用删除那个

"""这个文件的作用主要是用最小二乘法和EKF来进行一些角度的拟合函数"""
"""并且要控制这两个里面用哪个拟合方式的输出"""

class Omega:
    def __init__(self,delay_time:float=0.7)->None:
        ## 用到别的参数再说()
        ## 下面这一个函数是最小二乘法的参数
        self.track = None
        self.delay_time = delay_time
    # 这个函数就是在用很短时间的值来拟合一个最小二乘法的斜率()
    @staticmethod
    def estimate_omega(samples):
        # 这个是防止用太少的数来拟合一个十分离谱的东西
        if len(samples) < 3 :
            return 0.0
        t = np.array([s[0] for s in samples],dtype=float)
        a = np.array([s[1] for s in samples],dtype=float)
        deal_a = a[0] + np.unwarp(a-a[0])  # np.unwrap的作用就是将因为周期性的跳变重新写成原始数据，一般就是(-pi,pi]
        deal_t = t - t.mean()
        deal_t2 = float(np.sum(deal_t*deal_t))
        if deal_t2 < 1e-9:
            return 0.0
        omega = float(np.sum(deal_t*(deal_a-deal_a.mean()))/deal_t2)
        return max(-4.0,min(4.0,omega))
    
    def update_track(self,now:float,theta:float)->float:
        if self.track is None:
            self.track = {"sample":[(now,theta)],"theta":theta,"omega":0.0,"t":now,"settle":1}
            return 0.0
        dt = now-self.track["t"]
        # 后面这个max是合意为
        predicted = self.track["theta"] + self.track["omega"] * max(dt,0.0)
        jump = abs(geometry.wrap_pi(theta-predicted))
        if jump > 0.4:
            self.track = {"samples": [(now, theta)], "theta": theta,
                          "omega": 0.0, "t": now, "settle": 1}
            return 0.0
        self.track["samples"].append((now, theta))
        self.track["samples"] = [s for s in self.track["samples"] if now - s[0] <= 0.7]
        self.track["omega"] = self._estimate_omega(self.track["samples"])
        self.track["theta"] = theta
        self.track["t"] = now
        self.track["settle"] = min(self.track["settle"] + 1, 100)
        return self.track["omega"]
    
    def predict_theta(self, now: float, theta: float) -> float:
        omega = self.track["omega"] if self.track else 0.0
        if abs(omega) < 0.05:
            return theta
        point = geometry.target_point(self.side, theta)
        t_flight = geometry.flight_time(self.side, point, self.ball_speed)
        return theta + omega * (t_flight + self.delay_time)

K0 = 2.09

class BoundEKF:
    def __init__(self,a_bounds=(0.78,1.045),w_bounds=(1.884,2.000),K0 = 2.09):
        self.a_min,self.a_max = a_bounds
        self.w_min,self.w_max = w_bounds
        self.K0 = K0

    # 处理循环的函数()
    @staticmethod
    def wrap(x:float):
        return (x+np.pi)%(2.0*math.pi)-np.pi
    
    # sigmoid的tanh表达式，这个的目的是去控制数值的大小，因为sigmoid的特殊性
    @staticmethod
    def sig(u:float):
        return 0.5*(1.0+np.tanh(0.5*u))
    
    # 上面的函数的反函数
    @staticmethod
    def logit(s:float):
        s = np.clip(s,1e-4,1.0-1e-4)
        return np.log(s/(1.0-s))
    
    # 这个就是将用于EKF的值转化成真实的值
    def decode(self, ua:float, uw:float):
        return (self.a_min + (self.a_max - self.a_min)*self.sig(ua),
                self.w_min + (self.w_min - self.w_min)*self.sig(uw))
    
    #上面那个的导数
    def ddecode(self, ua:float, uw:float):
        sa, sw = self.sig(ua), self.sig(uw)
        return ((self.a_max - self.a_min)*sa*(1.0 - sa),
                (self.w_max - self.w_min)*sw*(1.0 - sw))

    # 将真实的数变成用于EKF的值
    def encode(self, a:float, w:float, margin:float=0.05):
        ra = np.clip((a - self.a_min)/(self.a_max - self.a_min), margin, 1.0 - margin)
        rw = np.clip((w - self.w_min)/(self.w_max - self.w_min), margin, 1.0 - margin)
        return self.logit(ra), self.logit(rw)


    def prop(self, x, dt):
        th, ua, uw, ph = x
        a, w = self.decode(ua, uw)
        wd = w*dt
        if abs(w) < 1e-6:
            s, c = np.sin(ph), np.cos(ph)
            dcos = dt*s + 0.5*w*dt*dt*c
            dcos_dw = 0.5*dt*dt*c
            dth_dph = a*dt*c
        else:
            c0, c1, s1 = np.cos(ph), np.cos(ph + wd), np.sin(ph + wd)
            dcos = (c0 - c1)/w
            dcos_dw = (dt*s1*w - (c0 - c1))/w**2
            dth_dph = a*(s1 - np.sin(ph))/w

        G = np.eye(4)
        G[0, 1] = -dt + dcos
        G[0, 2] = a*dcos_dw
        G[0, 3] = dth_dph
        G[3, 2] = dt

        da, dw = self.ddecode(ua, uw)
        F = np.eye(4)
        F[0, 1] = G[0, 1]*da
        F[0, 2] = G[0, 2]*dw
        F[0, 3] = G[0, 3]
        F[3, 2] = G[3, 2]*dw

        xn = np.array([th + (self.K0 - a)*dt + a*dcos, ua, uw, ph + wd])
        return xn, F

    # 将一个虚拟的状态变成物理状态
    def to_phys(self, x):
        a, w = self.decode(x[1], x[2])
        return np.array([x[0], a, w, x[3]])

    # 将协方差矩阵转换到物理空间()
    def cov_to_phys(self, P, ua, uw):
        da, dw = self.ddecode(ua, uw)
        D = np.diag([1.0, da, dw, 1.0])
        return D @ P @ D.T

    # ---- init ----------------------------------------------------------
    def init_scan(self, t, z, n_grid=2000):
        zu = np.unwrap(z)
        tau = t - t[0]
        best = None
        for w in np.linspace(self.w_min, self.w_max, n_grid):
            A = np.column_stack([np.ones_like(tau), tau, np.cos(w*tau), np.sin(w*tau)])
            coef, *_ = np.linalg.lstsq(A, zu, rcond=None)
            ssr = float(np.sum((zu - A @ coef)**2))
            if best is None or ssr < best[0]:
                best = (ssr, w, coef)
        ssr, w, (c0, c1, c2, c3) = best
        a = self.K0 - c1
        phi0 = float(np.arctan2(c3, -c2))
        return dict(a=float(a), w=float(w), l=phi0 - w*t[0], phi0=phi0,
                    ssr=ssr, sigma_hat=float(np.sqrt(ssr/max(1, tau.size - 4))))

    def run(self, t, z, sigma=None, T_init=8.0, q=(1e-8, 2e-6, 2e-6, 1e-8),
            sig_a=0.02, sig_w=0.01):
        t = np.asarray(t, float)
        z = np.asarray(z, float)
        m = t <= T_init
        ini = self.init_scan(t[m], z[m])
        if sigma is None:
            sigma = ini["sigma_hat"]
        ua0, uw0 = self.encode(ini["a"], ini["w"])
        da, dw = self.ddecode(ua0, uw0)
        x = np.array([z[0], ua0, uw0, ini["phi0"]])
        P = np.diag([0.05**2, (sig_a/da)**2, (sig_w/dw)**2, 0.1**2])
        n = t.size
        X = np.zeros((n, 4))
        Pp = np.zeros((n, 4, 4))
        I = np.eye(4)
        H = np.array([1.0, 0, 0, 0])
        Qd = np.diag(q)
        for k in range(n):
            if k > 0:
                dt = t[k] - t[k-1]
                x, F = self.prop(x, dt)
                P = F @ P @ F.T + Qd*dt
            X[k] = self.to_phys(x)
            Pp[k] = self.cov_to_phys(P, x[1], x[2])
            y = self.wrap(z[k] - x[0])
            S = P[0, 0] + sigma**2
            Kg = P[:, 0]/S
            x = x + Kg*y
            A = I - np.outer(Kg, H)
            P = A @ P @ A.T + sigma**2*np.outer(Kg, Kg)
        return X, Pp, ini

    def predict(self, x_phys, P_phys, T):
        ua, uw = self.encode(x_phys[1], x_phys[2])
        da, dw = self.ddecode(ua, uw)
        D = np.diag([1.0, da, dw, 1.0])
        Dinv = np.diag([1.0, 1.0/da, 1.0/dw, 1.0])
        x = np.array([x_phys[0], ua, uw, x_phys[3]])
        P = Dinv @ P_phys @ Dinv.T
        xs, F = self.prop(x, T)
        Pout = F @ P @ F.T
        sd = np.sqrt(max((self.cov_to_phys(Pout, xs[1], xs[2]))[0, 0], 0.0))
        return float(xs[0]), float(sd), self.to_phys(xs)


def simulate(a=0.9, w=1.94, l=0.7, theta0=0.2, T=40.0, fs=50.0, sigma=0.02, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, T, 1.0/fs)
    theta = theta0 + (K0 - a)*t + (a/w)*(np.cos(l) - np.cos(w*t + l))
    z = np.mod(theta + rng.normal(0.0, sigma, t.size), 2*np.pi)
    return t, z, theta