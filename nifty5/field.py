# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright(C) 2013-2018 Max-Planck-Society
#
# NIFTy is being developed at the Max-Planck-Institut fuer Astrophysik
# and financially supported by the Studienstiftung des deutschen Volkes.

from __future__ import absolute_import, division, print_function

import numpy as np

from . import dobj, utilities
from .compat import *
from .domain_tuple import DomainTuple


class Field(object):
    """ The discrete representation of a continuous field over multiple spaces.

    In NIFTy, Fields are used to store data arrays and carry all the needed
    metainformation (i.e. the domain) for operators to be able to work on them.

    Parameters
    ----------
    domain : DomainTuple
        the domain of the new Field

    val : data_object
        This object's global shape must match the domain shape
        After construction, the object will no longer be writeable!

    Notes
    -----
    If possible, do not invoke the constructor directly, but use one of the
    many convenience functions for Field construction!
    """

    def __init__(self, domain, val):
        self._uni = None
        if not isinstance(domain, DomainTuple):
            raise TypeError("domain must be of type DomainTuple")
        if not isinstance(val, dobj.data_object):
            if np.isscalar(val):
                self._uni = val
                val = dobj.uniform_full(domain.shape, val)
            else:
                raise TypeError("val must be of type dobj.data_object")
        if domain.shape != val.shape:
            raise ValueError("mismatch between the shapes of val and domain")
        self._domain = domain
        self._val = val
        dobj.lock(self._val)

    # prevent implicit conversion to bool
    def __nonzero__(self):
        raise TypeError("Field does not support implicit conversion to bool")

    def __bool__(self):
        raise TypeError("Field does not support implicit conversion to bool")

    @staticmethod
    def full(domain, val):
        """Creates a Field with a given domain, filled with a constant value.

        Parameters
        ----------
        domain : Domain, tuple of Domain, or DomainTuple
            domain of the new Field
        val : float/complex/int scalar
            fill value. Data type of the field is inferred from val.

        Returns
        -------
        Field
            the newly created field
        """
        if not np.isscalar(val):
            raise TypeError("val must be a scalar")
        if not (np.isreal(val) or np.iscomplex(val)):
            raise TypeError("need arithmetic scalar")
        domain = DomainTuple.make(domain)
        return Field(domain, val)

    @staticmethod
    def from_global_data(domain, arr, sum_up=False):
        """Returns a Field constructed from `domain` and `arr`.

        Parameters
        ----------
        domain : DomainTuple, tuple of Domain, or Domain
            the domain of the new Field
        arr : numpy.ndarray
            The data content to be used for the new Field.
            Its shape must match the shape of `domain`.
        sum_up : bool, optional
            If True, the contents of `arr` are summed up over all MPI tasks
            (if any), and the sum is used as data content.
            If False, the contens of `arr` are used directly, and must be
            identical on all MPI tasks.
        """
        return Field(DomainTuple.make(domain),
                     dobj.from_global_data(arr, sum_up))

    @staticmethod
    def from_local_data(domain, arr):
        return Field(DomainTuple.make(domain),
                     dobj.from_local_data(domain.shape, arr))

    def to_global_data(self):
        """Returns an array containing the full data of the field.

        Returns
        -------
        numpy.ndarray : array containing all field entries.
            Its shape is identical to `self.shape`.
        """
        return dobj.to_global_data(self._val)

    def to_global_data_rw(self):
        """Returns a modifiable array containing the full data of the field.

        Returns
        -------
        numpy.ndarray : array containing all field entries, which can be
            modified. Its shape is identical to `self.shape`.
        """
        return dobj.to_global_data_rw(self._val)

    @property
    def local_data(self):
        """numpy.ndarray : locally residing field data

        Returns a handle to the part of the array data residing on the local
        task (or to the entore array if MPI is not active).
        """
        return dobj.local_data(self._val)

    def cast_domain(self, new_domain):
        """Returns a field with the same data, but a different domain

        Parameters
        ----------
        new_domain : Domain, tuple of Domain, or DomainTuple
            The domain for the returned field. Must be shape-compatible to
            `self`.

        Returns
        -------
        Field
            Field living on `new_domain`, but with the same data as `self`.
        """
        return Field(DomainTuple.make(new_domain), self._val)

    @staticmethod
    def from_random(random_type, domain, dtype=np.float64, **kwargs):
        """ Draws a random field with the given parameters.

        Parameters
        ----------
        random_type : 'pm1', 'normal', or 'uniform'
            The random distribution to use.
        domain : DomainTuple
            The domain of the output random field
        dtype : type
            The datatype of the output random field

        Returns
        -------
        Field
            The newly created Field.
        """
        domain = DomainTuple.make(domain)
        return Field(domain=domain,
                     val=dobj.from_random(random_type, dtype=dtype,
                                          shape=domain.shape, **kwargs))

    @property
    def val(self):
        """dobj.data_object : the data object storing the field's entries

        Notes
        -----
        This property is intended for low-level, internal use only. Do not use
        from outside of NIFTy's core; there should be better alternatives.
        """
        return self._val

    @property
    def dtype(self):
        """type : the data type of the field's entries"""
        return self._val.dtype

    @property
    def domain(self):
        """DomainTuple : the field's domain"""
        return self._domain

    @property
    def shape(self):
        """tuple of int : the concatenated shapes of all sub-domains"""
        return self._domain.shape

    @property
    def size(self):
        """int : total number of pixels in the field"""
        return self._domain.size

    @property
    def real(self):
        """Field : The real part of the field"""
        if not np.issubdtype(self.dtype, np.complexfloating):
            return self
        return Field(self._domain, self._val.real)

    @property
    def imag(self):
        """Field : The imaginary part of the field"""
        if not np.issubdtype(self.dtype, np.complexfloating):
            raise ValueError(".imag called on a non-complex Field")
        return Field(self._domain, self._val.imag)

    def scalar_weight(self, spaces=None):
        """Returns the uniform volume element for a sub-domain of `self`.

        Parameters
        ----------
        spaces : int, tuple of int or None
            indices of the sub-domains of the field's domain to be considered.
            If `None`, the entire domain is used.

        Returns
        -------
        float or None
            if the requested sub-domain has a uniform volume element, it is
            returned. Otherwise, `None` is returned.
        """
        if np.isscalar(spaces):
            return self._domain[spaces].scalar_dvol

        if spaces is None:
            spaces = range(len(self._domain))
        res = 1.
        for i in spaces:
            tmp = self._domain[i].scalar_dvol
            if tmp is None:
                return None
            res *= tmp
        return res

    def total_volume(self, spaces=None):
        """Returns the total volume of a sub-domain of `self`.

        Parameters
        ----------
        spaces : int, tuple of int or None
            indices of the sub-domains of the field's domain to be considered.
            If `None`, the entire domain is used.

        Returns
        -------
        float
            the total volume of the requested sub-domain.
        """
        if np.isscalar(spaces):
            return self._domain[spaces].total_volume

        if spaces is None:
            spaces = range(len(self._domain))
        res = 1.
        for i in spaces:
            res *= self._domain[i].total_volume
        return res

    def weight(self, power=1, spaces=None):
        """ Weights the pixels of `self` with their invidual pixel-volume.

        Parameters
        ----------
        power : number
            The pixels get weighted with the volume-factor**power.

        spaces : None, int or tuple of int
            Determines on which sub-domain the operation takes place.
            If None, the entire domain is used.

        Returns
        -------
        Field
            The weighted field.
        """
        aout = self.local_data.copy()

        spaces = utilities.parse_spaces(spaces, len(self._domain))

        fct = 1.
        for ind in spaces:
            wgt = self._domain[ind].dvol
            if np.isscalar(wgt):
                fct *= wgt
            else:
                new_shape = np.ones(len(self.shape), dtype=np.int)
                new_shape[self._domain.axes[ind][0]:
                          self._domain.axes[ind][-1]+1] = wgt.shape
                wgt = wgt.reshape(new_shape)
                if dobj.distaxis(self._val) >= 0 and ind == 0:
                    # we need to distribute the weights along axis 0
                    wgt = dobj.local_data(dobj.from_global_data(wgt))
                aout *= wgt**power
        fct = fct**power
        if fct != 1.:
            aout *= fct

        return Field.from_local_data(self._domain, aout)

    def vdot(self, x=None, spaces=None):
        """ Computes the dot product of 'self' with x.

        Parameters
        ----------
        x : Field
            x must live on the same domain as `self`.

        spaces : None, int or tuple of int (default: None)
            The dot product is only carried out over the sub-domains in this
            tuple. If None, it is carried out over all sub-domains.

        Returns
        -------
        float, complex, either scalar (for full dot products)
                              or Field (for partial dot products)
        """
        if not isinstance(x, Field):
            raise TypeError("The dot-partner must be an instance of " +
                            "the NIFTy field class")

        if x._domain is not self._domain:
            raise ValueError("Domain mismatch")

        ndom = len(self._domain)
        spaces = utilities.parse_spaces(spaces, ndom)

        if len(spaces) == ndom:
            return dobj.vdot(self._val, x._val)
        # If we arrive here, we have to do a partial dot product.
        # For the moment, do this the explicit, non-optimized way
        return (self.conjugate()*x).sum(spaces=spaces)

    def norm(self):
        """ Computes the L2-norm of the field values.

        Returns
        -------
        float
            The L2-norm of the field values.
        """
        return np.sqrt(abs(self.vdot(x=self)))

    def squared_norm(self):
        """ Computes the square of the L2-norm of the field values.

        Returns
        -------
        float
            The square of the L2-norm of the field values.
        """
        return abs(self.vdot(x=self))

    def conjugate(self):
        """ Returns the complex conjugate of the field.

        Returns
        -------
        Field
            The complex conjugated field.
        """
        if np.issubdtype(self._val.dtype, np.complexfloating):
            return Field(self._domain, self._val.conjugate())
        return self

    # ---General unary/contraction methods---

    def __pos__(self):
        return self

    def __neg__(self):
        if self._uni is None:
            return Field(self._domain, -self._val)
        return Field(self._domain, -self._uni)

    def __abs__(self):
        if self._uni is None:
            return Field(self._domain, abs(self._val))
        return Field(self._domain, abs(self._uni))

    def _contraction_helper(self, op, spaces):
        if spaces is None:
            return getattr(self._val, op)()

        spaces = utilities.parse_spaces(spaces, len(self._domain))

        axes_list = tuple(self._domain.axes[sp_index] for sp_index in spaces)

        if len(axes_list) > 0:
            axes_list = reduce(lambda x, y: x+y, axes_list)

        # perform the contraction on the data
        data = getattr(self._val, op)(axis=axes_list)

        # check if the result is scalar or if a result_field must be constr.
        if np.isscalar(data):
            return data
        else:
            return_domain = tuple(dom
                                  for i, dom in enumerate(self._domain)
                                  if i not in spaces)

            return Field(DomainTuple.make(return_domain), data)

    def sum(self, spaces=None):
        """Sums up over the sub-domains given by `spaces`.

        Parameters
        ----------
        spaces : None, int or tuple of int (default: None)
            The summation is only carried out over the sub-domains in this
            tuple. If None, it is carried out over all sub-domains.

        Returns
        -------
        Field or scalar
            The result of the summation. If it is carried out over the entire
            domain, this is a scalar, otherwise a Field.
        """
        return self._contraction_helper('sum', spaces)

    def integrate(self, spaces=None):
        """Integrates over the sub-domains given by `spaces`.

        Integration is performed by summing over `self` multiplied by its
        volume factors.

        Parameters
        ----------
        spaces : None, int or tuple of int (default: None)
            The summation is only carried out over the sub-domains in this
            tuple. If None, it is carried out over all sub-domains.

        Returns
        -------
        Field or scalar
            The result of the integration. If it is carried out over the
            entire domain, this is a scalar, otherwise a Field.
        """
        swgt = self.scalar_weight(spaces)
        if swgt is not None:
            res = self.sum(spaces)
            res *= swgt
            return res
        tmp = self.weight(1, spaces=spaces)
        return tmp.sum(spaces)

    def prod(self, spaces=None):
        """Computes the product over the sub-domains given by `spaces`.

        Parameters
        ----------
        spaces : None, int or tuple of int (default: None)
            The operation is only carried out over the sub-domains in this
            tuple. If None, it is carried out over all sub-domains.

        Returns
        -------
        Field or scalar
            The result of the product. If it is carried out over the entire
            domain, this is a scalar, otherwise a Field.
        """
        return self._contraction_helper('prod', spaces)

    def all(self, spaces=None):
        return self._contraction_helper('all', spaces)

    def any(self, spaces=None):
        return self._contraction_helper('any', spaces)

#     def min(self, spaces=None):
#         """Determines the minimum over the sub-domains given by `spaces`.
#
#         Parameters
#         ----------
#         spaces : None, int or tuple of int (default: None)
#             The operation is only carried out over the sub-domains in this
#             tuple. If None, it is carried out over all sub-domains.
#
#         Returns
#         -------
#         Field or scalar
#             The result of the operation. If it is carried out over the entire
#             domain, this is a scalar, otherwise a Field.
#         """
#         return self._contraction_helper('min', spaces)
#
#     def max(self, spaces=None):
#         """Determines the maximum over the sub-domains given by `spaces`.
#
#         Parameters
#         ----------
#         spaces : None, int or tuple of int (default: None)
#             The operation is only carried out over the sub-domains in this
#             tuple. If None, it is carried out over all sub-domains.
#
#         Returns
#         -------
#         Field or scalar
#             The result of the operation. If it is carried out over the entire
#             domain, this is a scalar, otherwise a Field.
#         """
#         return self._contraction_helper('max', spaces)

    def mean(self, spaces=None):
        """Determines the mean over the sub-domains given by `spaces`.

        ``x.mean(spaces)`` is equivalent to
        ``x.integrate(spaces)/x.total_volume(spaces)``.

        Parameters
        ----------
        spaces : None, int or tuple of int (default: None)
            The operation is only carried out over the sub-domains in this
            tuple. If None, it is carried out over all sub-domains.

        Returns
        -------
        Field or scalar
            The result of the operation. If it is carried out over the entire
            domain, this is a scalar, otherwise a Field.
        """
        if self.scalar_weight(spaces) is not None:
            return self._contraction_helper('mean', spaces)
        # MR FIXME: not very efficient
        # MR FIXME: do we need "spaces" here?
        tmp = self.weight(1, spaces)
        return tmp.sum(spaces)*(1./tmp.total_volume(spaces))

    def var(self, spaces=None):
        """Determines the variance over the sub-domains given by `spaces`.

        Parameters
        ----------
        spaces : None, int or tuple of int (default: None)
            The operation is only carried out over the sub-domains in this
            tuple. If None, it is carried out over all sub-domains.

        Returns
        -------
        Field or scalar
            The result of the operation. If it is carried out over the entire
            domain, this is a scalar, otherwise a Field.
        """
        if self.scalar_weight(spaces) is not None:
            return self._contraction_helper('var', spaces)
        # MR FIXME: not very efficient or accurate
        m1 = self.mean(spaces)
        if np.issubdtype(self.dtype, np.complexfloating):
            sq = abs(self-m1)**2
        else:
            sq = (self-m1)**2
        return sq.mean(spaces)

    def std(self, spaces=None):
        """Determines the standard deviation over the sub-domains given by
        `spaces`.

        ``x.std(spaces)`` is equivalent to ``sqrt(x.var(spaces))``.

        Parameters
        ----------
        spaces : None, int or tuple of int (default: None)
            The operation is only carried out over the sub-domains in this
            tuple. If None, it is carried out over all sub-domains.

        Returns
        -------
        Field or scalar
            The result of the operation. If it is carried out over the entire
            domain, this is a scalar, otherwise a Field.
        """
        from .sugar import sqrt
        if self.scalar_weight(spaces) is not None:
            return self._contraction_helper('std', spaces)
        return sqrt(self.var(spaces))

    def __repr__(self):
        return "<nifty5.Field>"

    def __str__(self):
        return "nifty5.Field instance\n- domain      = " + \
               self._domain.__str__() + \
               "\n- val         = " + repr(self._val)

    def isEquivalentTo(self, other):
        """Determines (as quickly as possible) whether `self`'s content is
        identical to `other`'s content."""
        if self is other:
            return True
        if not isinstance(other, Field):
            return False
        if self._domain is not other._domain:
            return False
        return (self._val == other._val).all()

    def extract(self, dom):
        if dom is not self._domain:
            raise ValueError("domain mismatch")
        return self

    def unite(self, other):
        return self + other

    def positive_tanh(self):
        if self._uni is None:
            return 0.5*(1.+self.tanh())
        return Field(self._domain, 0.5*(1.+np.tanh(self._uni)))

    def __add__(self, other):
        # if other is a field, make sure that the domains match
        if isinstance(other, Field):
            if other._domain is not self._domain:
                raise ValueError("domains are incompatible.")
            if self._uni is None:
                if other._uni is None:
                    return Field(self._domain, self._val+other._val)
                if other._uni == 0:
                    return self
                return Field(self._domain, self._val+other._uni)
            else:
                if self._uni == 0:
                    return other
                if other._uni is None:
                    return Field(self._domain, other._val+self._uni)
                return Field(self._domain, self._uni+other._uni)

        if np.isscalar(other):
            if self._uni is None:
                return Field(self._domain, self._val+other)
            return Field(self._domain, self._uni+other)
        if isinstance(other, (dobj.data_object, np.ndarray)):
            return Field(self._domain, self._val+other)
        return NotImplemented

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        # if other is a field, make sure that the domains match
        if isinstance(other, Field):
            if other._domain is not self._domain:
                raise ValueError("domains are incompatible.")
            if self._uni is None:
                if other._uni is None:
                    return Field(self._domain, self._val-other._val)
                if other._uni == 0:
                    return self
                return Field(self._domain, self._val-other._uni)
            else:
                if self._uni == 0:
                    return -other
                if other._uni is None:
                    return Field(self._domain, self._uni-other._val)
                return Field(self._domain, self._uni-other._uni)

        if np.isscalar(other):
            if self._uni is None:
                return Field(self._domain, self._val-other)
            return Field(self._domain, self._uni-other)
        if isinstance(other, (dobj.data_object, np.ndarray)):
            return Field(self._domain, self._val-other)
        return NotImplemented

    def __mul__(self, other):
        # if other is a field, make sure that the domains match
        if isinstance(other, Field):
            if other._domain is not self._domain:
                raise ValueError("domains are incompatible.")
            if self._uni is None:
                if other._uni is None:
                    return Field(self._domain, self._val*other._val)
                if other._uni == 1:
                    return self
                if other._uni == 0:
                    return other
                return Field(self._domain, self._val*other._uni)
            else:
                if self._uni == 1:
                    return other
                if self._uni == 0:
                    return self
                if other._uni is None:
                    return Field(self._domain, other._val*self._uni)
                return Field(self._domain, self._uni*other._uni)

        if np.isscalar(other):
            if self._uni is None:
                if other == 1:
                    return self
                if other == 0:
                    return Field(self._domain, other)
                return Field(self._domain, self._val*other)
            return Field(self._domain, self._uni*other)
        if isinstance(other, (dobj.data_object, np.ndarray)):
            return Field(self._domain, self._val*other)
        return NotImplemented


for op in ["__rsub__",
           "__rmul__",
           "__div__", "__rdiv__",
           "__truediv__", "__rtruediv__",
           "__floordiv__", "__rfloordiv__",
           "__pow__", "__rpow__",
           "__lt__", "__le__", "__gt__", "__ge__", "__eq__", "__ne__"]:
    def func(op):
        def func2(self, other):
            # if other is a field, make sure that the domains match
            if isinstance(other, Field):
                if other._domain is not self._domain:
                    raise ValueError("domains are incompatible.")
                tval = getattr(self._val, op)(other._val)
                return Field(self._domain, tval)

            if (np.isscalar(other) or
                    isinstance(other, (dobj.data_object, np.ndarray))):
                tval = getattr(self._val, op)(other)
                return Field(self._domain, tval)

            return NotImplemented
        return func2
    setattr(Field, op, func(op))

for op in ["__iadd__", "__isub__", "__imul__", "__idiv__",
           "__itruediv__", "__ifloordiv__", "__ipow__"]:
    def func(op):
        def func2(self, other):
            raise TypeError(
                "In-place operations are deliberately not supported")
        return func2
    setattr(Field, op, func(op))

for f in ["sqrt", "exp", "log", "tanh"]:
    def func(f):
        def func2(self):
            if self._uni is None:
                fu = getattr(dobj, f)
                return Field(domain=self._domain, val=fu(self.val))
            else:
                fu = getattr(np, f)
                return Field(domain=self._domain, val=fu(self._uni))
        return func2
    setattr(Field, f, func(f))
