from time import time

import matplotlib.pyplot as plt
import numpy as np

import nifty5 as ift

ift.fft.enable_fftw()
np.random.seed(40)

N0s, a0s, b0s, c0s = [], [], [], []
N1s, a1s, b1s, c1s = [], [], [], []

for ii in range(1, 8):
    nu = 1024
    nv = 1024
    N = int(10**ii)
    print('N = {}'.format(N))

    uv = np.random.rand(N, 2) - 0.5
    vis = np.random.randn(N) + 1j*np.random.randn(N)

    uvspace = ift.RGSpace((nu, nv))

    visspace = ift.UnstructuredDomain(N)

    img = np.random.randn(nu*nv)
    img = img.reshape((nu, nv))
    img = ift.from_global_data(uvspace, img)

    t0 = time()
    GM = ift.GridderMaker(uvspace, eps=1e-7)
    idx = GM.getReordering(uv)
    uv = uv[idx]
    vis = vis[idx]
    vis = ift.from_global_data(visspace, vis)
    op = GM.getFull(uv).adjoint
    t1 = time()
    op(img).to_global_data()
    t2 = time()
    op.adjoint(vis).to_global_data()
    t3 = time()
    N0s.append(N)
    a0s.append(t1 - t0)
    b0s.append(t2 - t1)
    c0s.append(t3 - t2)

    t0 = time()
    op = ift.NFFT(uvspace, uv)
    t1 = time()
    op(img).to_global_data()
    t2 = time()
    op.adjoint(vis).to_global_data()
    t3 = time()
    N1s.append(N)
    a1s.append(t1 - t0)
    b1s.append(t2 - t1)
    c1s.append(t3 - t2)

print('Measure rest operator')
sc = ift.StatCalculator()
op = GM.getRest().adjoint
for _ in range(10):
    t0 = time()
    res = op(img)
    sc.add(time() - t0)
t_fft = sc.mean
print('FFT shape', res.shape)

plt.scatter(N0s, a0s, label='Gridder mr')
plt.scatter(N1s, a1s, marker='^', label='NFFT')
plt.legend()
plt.ylabel('time [s]')
plt.title('Initialization')
plt.loglog()
plt.savefig('bench0.png')
plt.close()

plt.scatter(N0s, b0s, color='k', marker='^', label='Gridder mr times')
plt.scatter(N1s, b1s, color='r', marker='^', label='NFFT times')
plt.scatter(N0s, c0s, color='k', label='Gridder mr adjoint times')
plt.scatter(N1s, c1s, color='r', label='NFFT adjoint times')
plt.axhline(sc.mean, label='FFT')
plt.axhline(sc.mean + np.sqrt(sc.var))
plt.axhline(sc.mean - np.sqrt(sc.var))
plt.legend()
plt.ylabel('time [s]')
plt.title('Apply')
plt.loglog()
plt.savefig('bench1.png')
plt.close()
