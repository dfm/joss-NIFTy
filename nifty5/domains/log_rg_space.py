from functools import reduce
from ..sugar import exp

import numpy as np

from .. import dobj
from ..field import Field
from .structured_domain import StructuredDomain


class LogRGSpace(StructuredDomain):

    _needed_for_hash = ['_shape', '_bindistances', '_t_0', '_harmonic']

    def __init__(self, shape, bindistances, t_0, harmonic=False):
        super(LogRGSpace, self).__init__()

        self._harmonic = bool(harmonic)

        if np.isscalar(shape):
            shape = (shape,)
        self._shape = tuple(int(i) for i in shape)

        self._bindistances = tuple(bindistances)
        self._t_0 = tuple(t_0)

        self._dim = int(reduce(lambda x, y: x * y, self._shape))
        self._dvol = float(reduce(lambda x, y: x * y, self._bindistances))

    @property
    def harmonic(self):
        return self._harmonic

    @property
    def shape(self):
        return self._shape

    def scalar_dvol(self):
        return self._dvol

    @property
    def bindistances(self):
        return np.array(self._bindistances)

    @property
    def size(self):
        return np.prod(self._shape)

    @property
    def t_0(self):
        return np.array(self._t_0)

    def __repr__(self):
        return ("LogRGSpace(shape=%r, harmonic=%r)"
                % (self.shape, self.harmonic))

    def get_default_codomain(self):
        if self._harmonic:
            raise ValueError("only supported for nonharmonic space")
        codomain_bindistances = 1. / (self.bindistances * self.shape)
        return LogRGSpace(self.shape, codomain_bindistances,
                          np.zeros(len(self.shape)), True)

    def get_k_length_array(self):
        ib = dobj.ibegin_from_shape(self._shape)
        res = np.arange(self.local_shape[0], dtype=np.float64) + ib[0]
        res = np.minimum(res, self.shape[0]-res)*self.bindistances[0]
        if len(self.shape) == 1:
            return Field.from_local_data(self, res)
        res *= res
        for i in range(1, len(self.shape)):
            tmp = np.arange(self.local_shape[i], dtype=np.float64) + ib[i]
            tmp = np.minimum(tmp, self.shape[i]-tmp)*self.bindistances[i]
            tmp *= tmp
            res = np.add.outer(res, tmp)
        return Field.from_local_data(self, np.sqrt(res))

    def get_expk_length_array(self):
        # FIXME This is a hack! Only for plotting. Seems not to be the final version.
        out = exp(self.get_k_length_array()).to_global_data().copy()
        out[1:] = out[:-1]
        out[0] = 0
        return Field.from_global_data(self, out)
