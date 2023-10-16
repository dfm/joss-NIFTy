#!/usr/bin/env python
# %% [markdown]
# # Nonlinear Models in NIFTy

# 1. Posterior: We would like to know $P(\theta|d)$ with $\theta$ the sky
#    brightness and $d$ measured count data of the sky brightness
# 1. Likelihood: We assume that $P(d|\theta)$ is a Poisson distribution
# 1. Prior: We assume that the sky brightness is a priori log-normal and
#    $\log \theta$ is spatially smooth
#
# To build a model in NIFTy, we go bottom and start from the prior, next we
# define the likelihood and finally retrieve (an approximation to) the posterior.

# %%
import nifty8 as ift

# %% [markdown]
# ## Prior
#
# In NIFTy, we always start from a standard normal prior.
# Thus, instead of trying to directly create a smooth log-normal $\theta$, we
# instead ask ourselves (1) how we can make a standard normal smooth and
# afterwards (2) how we can make it log-normal.

# %%
position_space = ift.RGSpace([64, 64])  # domain on which our parameters live


# We need to apply the sqrt of the power spectrum to give a standard normal
# prior the desired power spectrum.
def power_spectrum_sqrt(k):
    return (1.0 / (20.0 + k**4))**0.5


p_space = ift.PowerSpace(position_space.get_default_codomain())
pd = ift.PowerDistributor(position_space.get_default_codomain(), p_space)

a = ift.PS_field(p_space, power_spectrum_sqrt)
amplitude = pd(a)
amplitude = ift.makeOp(amplitude)
harmonic2pos = ift.HarmonicTransformOperator(amplitude.target, position_space)

# %%
r = ift.from_random(amplitude.domain)
ift.single_plot(harmonic2pos(amplitude(r)))
# YAY, we achieved (1)

# %%
# Let's make it log-normal distributed. To do so we really only have to
# exponentiate it.
r = ift.from_random(amplitude.domain)
harmonic2pos = ift.HarmonicTransformOperator(amplitude.target, position_space)
ift.single_plot(ift.exp(harmonic2pos(amplitude(r))))

# %%

# We can also apply the operators to one another to retrieve a new operator that
# joins all of them. Here we create an operator to propagate our a prior
# standard normal distributed parameters to a smooth log-normal distributed
# parameter.
signal = ift.exp(harmonic2pos(amplitude))
# YAY, we achieved (2)!

# %% [markdown]
# ## Likelihood
#
# We've done (1) and (2). Next, let us look at the likelihood $P(d|\theta)$.

# %%
r = ift.from_random(signal.domain)
synthetic_signal_realization = signal(r)

# Retrieve synthetic data from our model
rng = ift.random.current_rng()  # numpy random number generator
synthetic_data = rng.poisson(
    lam=synthetic_signal_realization.val, size=position_space.shape
)

synthetic_data = ift.makeField(position_space, synthetic_data)
likelihood = ift.PoissonianEnergy(synthetic_data)

# %% [markdown]
# ## Posterior
#
# We now have our prior model and our likelihood model.
# Let's do some inference!

# %%
forward = likelihood @ signal
forward = forward.ducktape("domain")  # HACK to make `optimize_vi` happy

ic_sampling = ift.DeltaEnergyController(
    name="Sampling", iteration_limit=100, tol_rel_deltaE=1e-8
)
ic_newton = ift.DeltaEnergyController(
    name="Newton", iteration_limit=100, tol_rel_deltaE=1e-8
)
minimizer = ift.NewtonCG(ic_newton)
n_vi_iterations = 2
n_samples = 10

state = ift.optimize_kl(
    forward,
    n_vi_iterations,
    n_samples=n_samples,
    kl_minimizer=minimizer,
    sampling_iteration_controller=ic_sampling,
    nonlinear_sampling_minimizer=None
)

# %%
posterior_signal_samples = [
    signal.ducktape("domain")(sample) for sample in state.iterator()
]
p = ift.Plot()
p.add(synthetic_data, title="Synthetic Data")
for i in range(3):  # Show the first three samples
    p.add(posterior_signal_samples[i], title=f"Sample {i+1:02d}")
p.output()

# %%
p = ift.Plot()
m, v = state.sample_stat(signal.ducktape("domain"))
s = v**0.5
p.add(synthetic_signal_realization, title="Synthetic Signal Realization")
p.add(m, title="Posterior Mean")
p.add(s, title="Posterior Standard Deviation")
p.add(s / m, title="Posterior Relative Uncertainty")
p.output()
