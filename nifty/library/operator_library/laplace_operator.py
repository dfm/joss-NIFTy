
import numpy as np
from nifty import Field,\
                  EndomorphicOperator,\
                  PowerSpace
import nifty.nifty_utilities as utilities

# def _irregular_nabla(x,k):
#     #applies forward differences and does nonesense at the edge. Thus needs cutting
#     y = -x
#     y[:-1] += x[1:]
#     y[1:-1] /= - k[1:-1] + k[2:]
#     return y
#
# def _irregular_adj_nabla(z, k):
#     #applies backwards differences*(-1) and does nonesense at the edge. Thus needs cutting
#     x = z.copy()
#     x[1:-1] /= - k[1:-1] + k[2:]
#     y = -x
#     y[1:] += x[:-1]
#     return y


class LaplaceOperator(EndomorphicOperator):
    """A irregular LaplaceOperator with free boundary and excluding monopole.

    This LaplaceOperator implements the second derivative of a Field in PowerSpace
    on logarithmic or linear scale with vanishing curvature at the boundary, starting
    at the second entry of the Field. The second derivative of the Field on the irregular grid
    is calculated using finite differences.

    Parameters
    ----------
    logarithmic : boolean,
        Whether smoothness is calculated on a logarithmic scale or linear scale
        default : True
    """

    def __init__(self, domain,
                 default_spaces=None, logarithmic = True):
        super(LaplaceOperator, self).__init__(default_spaces)
        if (domain is not None):
            if (not isinstance(domain, PowerSpace)):
                raise TypeError("The domain has to live over a PowerSpace")
        self._domain = self._parse_domain(domain)
        if logarithmic :
            self.positions = self.domain[0].kindex.copy()
            self.positions[1:] = np.log(self.positions[1:])
            self.positions[0] = -1.
        else :
            self.positions = self.domain[0].kindex.copy()
            self.positions[0] = -1

        self.fwd_dist = self.positions[1:] - self.positions[:-1]

    @property
    def target(self):
        return self._domain

    @property
    def domain(self):
        return self._domain

    @property
    def unitary(self):
        return False

    @property
    def symmetric(self):
        return False

    @property
    def self_adjoint(self):
        return False


    def _times(self, x, spaces):
        spaces = utilities.cast_axis_to_tuple(spaces, len(x.domain))
        if spaces is None:
            # this case means that x lives on only one space, which is
            # identical to the space in the domain of `self`. Otherwise the
            # input check of LinearOperator would have failed.
            axes = x.domain_axes[0]
        else:
            axes = x.domain_axes[spaces[0]]
        axis = axes[0]
        prefix = (slice(None),) * axis
        fwd_dist = self.fwd_dist.reshape((1,)*axis + self.fwd_dist.shape)
        positions = self.positions.reshape((1,)*axis + self.positions.shape)
        ret = x.val.copy_empty()
        x = x.val
        ret[prefix + (slice(1,-1),)] = -(x[prefix + (slice(1,-1),)]
                                         - x[prefix + (slice(0,-2),)]) / fwd_dist[prefix + (slice(0,-1),)] \
                    + (x[prefix + (slice(2,None),)] - x[prefix + (slice(1,-1),)]) / fwd_dist[prefix + (slice(1, None),)]
        ret[prefix + (slice(1,-1),)] /= positions[prefix + (slice(2,None),)] - positions[prefix + (slice(None,-2),)]
        ret *= 2.
        ret[prefix + (slice(0,2),)] = 0
        ret[prefix + (slice(-1,-1),)] = 0
        ret[prefix + (slice(2,None),)] *= np.sqrt(fwd_dist)[prefix + (slice(1,None),)]
        return Field(self.domain, val=ret).weight(power=-0.5,spaces=spaces)

    def _adjoint_times(self, x, spaces):
        spaces = utilities.cast_axis_to_tuple(spaces, len(x.domain))
        if spaces is None:
            # this case means that x lives on only one space, which is
            # identical to the space in the domain of `self`. Otherwise the
            # input check of LinearOperator would have failed.
            axes = x.domain_axes[0]
        else:
            axes = x.domain_axes[spaces[0]]
        axis = axes[0]
        prefix = (slice(None),) * axis
        fwd_dist = self.fwd_dist.reshape((1,)*axis + self.fwd_dist.shape)
        positions = self.positions.reshape((1,)*axis + self.positions.shape)
        y = x.copy().weight(power=0.5).val
        y[prefix + (slice(2,None),)] *= np.sqrt(fwd_dist)[prefix + (slice(1,None),)]
        y[prefix + (slice(0,2),)] = 0
        y[prefix + (slice(-1,-1),)] = 0
        ret = y.copy_empty()
        y[prefix + (slice(1,-1),)] /= positions[prefix + (slice(2,None),)] - positions[prefix + (slice(None,-2),)]
        y *= 2
        ret[prefix + (slice(1,-1),)] = -y[prefix + (slice(1,-1),)] / fwd_dist[prefix \
                                        + (slice(0,-1),)] - y[prefix
                                                    + (slice(1,-1),)] / fwd_dist[prefix + (slice(1, None),)]
        ret[prefix + (slice(0,-2),)] += y[prefix + (slice(1,-1),)] / fwd_dist[prefix + (slice(0,-1),)]
        ret[prefix + (slice(2,None),)] += y[prefix + (slice(1,-1),)] / fwd_dist[prefix + (slice(1, None),)]
        return Field(self.domain, val=ret).weight(-1,spaces=spaces)

    def _irregular_laplace(self, x):
        ret = np.zeros_like(x)
        ret[1:-1] = -(x[1:-1] - x[0:-2]) / self.fwd_dist[:-1] \
                    + (x[2:] - x[1:-1]) / self.fwd_dist[1:]
        ret[1:-1] /= self.positions[2:] - self.positions[:-2]
        ret *= 2.
        return ret

    def _irregular_adj_laplace(self, x):
        ret = np.zeros_like(x)
        y = x.copy()
        y[1:-1] /= self.positions[2:] - self.positions[:-2]
        y *= 2
        ret[1:-1] = -y[1:-1] / self.fwd_dist[:-1] - y[1:-1] / self.fwd_dist[1:]
        ret[0:-2] += y[1:-1] / self.fwd_dist[:-1]
        ret[2:] += y[1:-1] / self.fwd_dist[1:]
        return ret
