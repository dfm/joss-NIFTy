# NIFTy
# Copyright (C) 2017  Theo Steininger
#
# Author: Theo Steininger
#
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

from __future__ import division
import numpy as np

from keepers import Versionable,\
                    Loggable

from d2o import distributed_data_object,\
    STRATEGIES as DISTRIBUTION_STRATEGIES

from nifty.config import nifty_configuration as gc

from nifty.domain_object import DomainObject

from nifty.spaces.power_space import PowerSpace

import nifty.nifty_utilities as utilities
from nifty.random import Random


class Field(Loggable, Versionable, object):
    """ The discrete representation of a continuous field over multiple spaces.

    In NIFTY, Fields are used to store data arrays and carry all the needed
    metainformation (i.e. the domain) for operators to be able to work on them.
    In addition Field has methods to work with power-spectra.

    Parameters
    ----------
    domain : DomainObject
        One of the space types NIFTY supports. RGSpace, GLSpace, HPSpace,
        LMSpace or PowerSpace. It might also be a FieldArray, which is
        an unstructured domain.

    val : scalar, numpy.ndarray, distributed_data_object, Field
        The values the array should contain after init. A scalar input will
        fill the whole array with this scalar. If an array is provided the
        array's dimensions must match the domain's.

    dtype : type
        A numpy.type. Most common are int, float and complex.

    distribution_strategy: optional[{'fftw', 'equal', 'not', 'freeform'}]
        Specifies which distributor will be created and used.
        'fftw'      uses the distribution strategy of pyfftw,
        'equal'     tries to  distribute the data as uniform as possible
        'not'       does not distribute the data at all
        'freeform'  distribute the data according to the given local data/shape

    copy: boolean

    Attributes
    ----------
    val : distributed_data_object

    domain : DomainObject
        See Parameters.
    domain_axes : tuple of tuples
        Enumerates the axes of the Field
    dtype : type
        Contains the datatype stored in the Field.
    distribution_strategy : string
        Name of the used distribution_strategy.

    Raise
    -----
    TypeError
        Raised if
            *the given domain contains something that is not a DomainObject
             instance
            *val is an array that has a different dimension than the domain

    Examples
    --------
    >>> a = Field(RGSpace([4,5]),val=2)
    >>> a.val
    <distributed_data_object>
    array([[2, 2, 2, 2, 2],
           [2, 2, 2, 2, 2],
           [2, 2, 2, 2, 2],
           [2, 2, 2, 2, 2]])
    >>> a.dtype
    dtype('int64')

    See Also
    --------
    distributed_data_object

    """
    # ---Initialization methods---

    def __init__(self, domain=None, val=None, dtype=None,
                 distribution_strategy=None, copy=False):

        self.domain = self._parse_domain(domain=domain, val=val)
        self.domain_axes = self._get_axes_tuple(self.domain)

        self.dtype = self._infer_dtype(dtype=dtype,
                                       val=val)

        self.distribution_strategy = self._parse_distribution_strategy(
                                distribution_strategy=distribution_strategy,
                                val=val)

        if val is None:
            self._val = None
        else:
            self.set_val(new_val=val, copy=copy)

    def _parse_domain(self, domain, val=None):
        """ Returns a tuple of DomainObjects for nomenclature unification.

        Parameters
        ----------
        domain : all supported NIFTY spaces
            The domain over which the Field lives.
        val : a NIFTY Field instance
            Can be used to make Field infere it's domain by adopting val's
            domain.

        Returns
        -------
        out : tuple
            The output object. A tuple with one or multiple DomainObjects.
        """
        if domain is None:
            if isinstance(val, Field):
                domain = val.domain
            else:
                domain = ()
        elif isinstance(domain, DomainObject):
            domain = (domain,)
        elif not isinstance(domain, tuple):
            domain = tuple(domain)

        for d in domain:
            if not isinstance(d, DomainObject):
                raise TypeError(
                    "Given domain contains something that is not a "
                    "DomainObject instance.")
        return domain

    def _get_axes_tuple(self, things_with_shape, start=0):
        """ Enumerates all axes of the domain.

        This function is used in the greater context of the 'spaces' keyword.

        Parameters
        ----------
        things_with_shape : indexable list of objects with .shape property
            Normal input is a domain/ tuple of domains.
        start : int
            Sets the integer number for the first axis

        Returns
        -------
        out : tuple
            Incremental numeration of all axes.

        Note
        ----

        The 'spaces' keyword is used in operators in order to carry out
        operations only on a certain subspace if the domain of the Field is
        a product space.
        """
        i = start
        axes_list = []
        for thing in things_with_shape:
            l = []
            for j in range(len(thing.shape)):
                l += [i]
                i += 1
            axes_list += [tuple(l)]
        return tuple(axes_list)

    def _infer_dtype(self, dtype, val):
        """ Inferes the datatype of the Field

        Parameters
        ----------
        dtype : type
            Can be None
        val : list of arrays
            If the dtype is None, Fields tries to infere the datatype from the
            values given to it at initialization.

        Returns
        -------
        out : np.dtype
        """
        if dtype is None:
            try:
                dtype = val.dtype
            except AttributeError:
                try:
                    if val is None:
                        raise TypeError
                    dtype = np.result_type(val)
                except(TypeError):
                    dtype = np.dtype(gc['default_field_dtype'])
        else:
            dtype = np.dtype(dtype)

        return dtype

    def _parse_distribution_strategy(self, distribution_strategy, val):
        if distribution_strategy is None:
            if isinstance(val, distributed_data_object):
                distribution_strategy = val.distribution_strategy
            elif isinstance(val, Field):
                distribution_strategy = val.distribution_strategy
            else:
                self.logger.debug("distribution_strategy set to default!")
                distribution_strategy = gc['default_distribution_strategy']
        elif distribution_strategy not in DISTRIBUTION_STRATEGIES['global']:
            raise ValueError(
                    "distribution_strategy must be a global-type "
                    "strategy.")
        return distribution_strategy

    # ---Factory methods---

    @classmethod
    def from_random(cls, random_type, domain=None, dtype=None,
                    distribution_strategy=None, **kwargs):
        """ Draws a random field with the given parameters.

        Parameters
        ----------
        cls : class

        random_type : String
            'pm1', 'normal', 'uniform' are the supported arguments for this
            method.

        domain : DomainObject
            The domain of the output random field

        dtype : type
            The datatype of the output random field

        distribution_strategy : all supported distribution strategies
            The distribution strategy of the output random field

        Returns
        -------
        out : Field
            The output object.

        See Also
        --------
        _parse_random_arguments, power_synthesise

        """
        # create a initially empty field
        f = cls(domain=domain, dtype=dtype,
                distribution_strategy=distribution_strategy)

        # now use the processed input in terms of f in order to parse the
        # random arguments
        random_arguments = cls._parse_random_arguments(random_type=random_type,
                                                       f=f,
                                                       **kwargs)

        # extract the distributed_data_object from f and apply the appropriate
        # random number generator to it
        sample = f.get_val(copy=False)
        generator_function = getattr(Random, random_type)
        sample.apply_generator(
            lambda shape: generator_function(dtype=f.dtype,
                                             shape=shape,
                                             **random_arguments))
        return f

    @staticmethod
    def _parse_random_arguments(random_type, f, **kwargs):
        if random_type == "pm1":
            random_arguments = {}

        elif random_type == "normal":
            mean = kwargs.get('mean', 0)
            std = kwargs.get('std', 1)
            random_arguments = {'mean': mean,
                                'std': std}

        elif random_type == "uniform":
            low = kwargs.get('low', 0)
            high = kwargs.get('high', 1)
            random_arguments = {'low': low,
                                'high': high}

        else:
            raise KeyError(
                "unsupported random key '" + str(random_type) + "'.")

        return random_arguments

    # ---Powerspectral methods---

    def power_analyze(self, spaces=None, log=False, nbin=None, binbounds=None,
                      real_signal=True):
        """ Computes the powerspectrum of the Field

        Creates a PowerSpace with the given attributes and computes the
        power spectrum as a field over this PowerSpace.
        It's important to note that this can only be done if the subspace to
        be analyzed is in harmonic space.

        Parameters
        ----------
        spaces : int, *optional*
            The subspace which you want to have the powerspectrum of.
            {default : None}
                if spaces==None : Tries to synthesize for the whole domain

        log : boolean, *optional*
            True if the output PowerSpace should have log binning.
            {default : False}

        nbin : int, None, *optional*
            The number of bins the resulting PowerSpace shall have.
            {default : None}
                if nbin==None : maximum number of bins is used

        binbounds : array-like, None, *optional*
            Inner bounds of the bins, if specifield
            {default : None}
                if binbounds==None : bins are inferred. Overwrites nbins and log
        real_signal : boolean, *optional*
            Whether the analysed signal-space Field is real or complex.
            For a real field a complex power spectrum comes out.
            For a compex field all power is put in a real power spectrum.
            {default : True}
        Raise
        -----
        ValueError
            Raised if
                *len(spaces) is either 0 or >1
                *len(domain) is not 1 with spaces=None
                *the analyzed space is not harmonic

        Returns
        -------
        out : Field
            The output object. It's domain is a PowerSpace and it contains
            the power spectrum of 'self's field.

        See Also
        --------
        power_synthesize, PowerSpace
        """
        # check if all spaces in `self.domain` are either harmonic or
        # power_space instances
        for sp in self.domain:
            if not sp.harmonic and not isinstance(sp, PowerSpace):
                self.logger.info(
                    "Field has a space in `domain` which is neither "
                    "harmonic nor a PowerSpace.")

        # check if the `spaces` input is valid
        spaces = utilities.cast_axis_to_tuple(spaces, len(self.domain))
        if spaces is None:
            if len(self.domain) == 1:
                spaces = (0,)
            else:
                raise ValueError(
                    "Field has multiple spaces as domain "
                    "but `spaces` is None.")

        if len(spaces) == 0:
            raise ValueError(
                "No space for analysis specified.")
        elif len(spaces) > 1:
            raise ValueError(
                "Conversion of only one space at a time is allowed.")

        space_index = spaces[0]

        if not self.domain[space_index].harmonic:
            raise ValueError(
                "The analyzed space must be harmonic.")

        # Create the target PowerSpace instance:
        # If the associated signal-space field was real, we extract the
        # hermitian and anti-hermitian parts of `self` and put them
        # into the real and imaginary parts of the power spectrum.
        # If it was complex, all the power is put into a real power spectrum.

        distribution_strategy = \
            self.val.get_axes_local_distribution_strategy(
                self.domain_axes[space_index])

        harmonic_domain = self.domain[space_index]
        power_domain = PowerSpace(harmonic_domain=harmonic_domain,
                                  distribution_strategy=distribution_strategy,
                                  log=log, nbin=nbin, binbounds=binbounds)

        # extract pindex and rho from power_domain
        pindex = power_domain.pindex
        rho = power_domain.rho

        if real_signal:
            hermitian_part, anti_hermitian_part = \
                harmonic_domain.hermitian_decomposition(
                                            self.val,
                                            axes=self.domain_axes[space_index])

            [hermitian_power, anti_hermitian_power] = \
                [self._calculate_power_spectrum(
                                            x=part,
                                            pindex=pindex,
                                            rho=rho,
                                            axes=self.domain_axes[space_index])
                 for part in [hermitian_part, anti_hermitian_part]]

            power_spectrum = hermitian_power + 1j * anti_hermitian_power
        else:
            power_spectrum = self._calculate_power_spectrum(
                                            x=self.val,
                                            pindex=pindex,
                                            rho=rho,
                                            axes=self.domain_axes[space_index])

        # create the result field and put power_spectrum into it
        result_domain = list(self.domain)
        result_domain[space_index] = power_domain

        if real_signal:
            result_dtype = np.complex
        else:
            result_dtype = np.float

        result_field = self.copy_empty(
                   domain=result_domain,
                   dtype=result_dtype,
                   distribution_strategy=power_spectrum.distribution_strategy)
        result_field.set_val(new_val=power_spectrum, copy=False)

        return result_field

    def _calculate_power_spectrum(self, x, pindex, rho, axes=None):
        fieldabs = abs(x)
        fieldabs **= 2

        if axes is not None:
            pindex = self._shape_up_pindex(
                                    pindex=pindex,
                                    target_shape=x.shape,
                                    target_strategy=x.distribution_strategy,
                                    axes=axes)
        power_spectrum = pindex.bincount(weights=fieldabs,
                                         axis=axes)
        if axes is not None:
            new_rho_shape = [1, ] * len(power_spectrum.shape)
            new_rho_shape[axes[0]] = len(rho)
            rho = rho.reshape(new_rho_shape)
        power_spectrum /= rho

        power_spectrum **= 0.5
        return power_spectrum

    def _shape_up_pindex(self, pindex, target_shape, target_strategy, axes):
        if pindex.distribution_strategy not in \
                DISTRIBUTION_STRATEGIES['global']:
            raise ValueError("pindex's distribution strategy must be "
                             "global-type")

        if pindex.distribution_strategy in DISTRIBUTION_STRATEGIES['slicing']:
            if ((0 not in axes) or
                    (target_strategy is not pindex.distribution_strategy)):
                raise ValueError(
                    "A slicing distributor shall not be reshaped to "
                    "something non-sliced.")

        semiscaled_shape = [1, ] * len(target_shape)
        for i in axes:
            semiscaled_shape[i] = target_shape[i]
        local_data = pindex.get_local_data(copy=False)
        semiscaled_local_data = local_data.reshape(semiscaled_shape)
        result_obj = pindex.copy_empty(global_shape=target_shape,
                                       distribution_strategy=target_strategy)
        result_obj.set_full_data(semiscaled_local_data, copy=False)

        return result_obj

    def power_synthesize(self, spaces=None, real_power=True, real_signal=True,
                         mean=None, std=None):
        """Yields a random field in harmonic space with this power spectrum.

        This method draws a Gaussian random field in the harmic partner domain.
        The drawn field has this field as its power spectrum.

        Notes
        -----
        For this the domain must be a PowerSpace.

        Parameters
        ----------
        spaces : {tuple, int, None} *optional*
            Specifies the subspace in which the power will be synthesized in
            case of a product space.
            {default : None}
                if spaces==None : Tries to synthesize for the whole domain

        real_power : boolean *optional*
            Determines whether the power spectrum is real or complex
            {default : True}

        real_signal : boolean *optional*
            True will result in a purely real signal-space field.
            This means that the created field is symmetric wrt. the origin
            after complex conjugation.
            {default : True}
        mean : {float, None} *optional*
            The mean of the noise field the powerspectrum will be multiplied on.
            {default : None}
                if mean==None : mean will be set to 0
        std : float *optional*
            The standard deviation of the noise field the powerspectrum will be
            multiplied on.
            {default : None}
                if std==None : std will be set to 1

        Returns
        -------
        out : Field
            The output object. A random field created with the power spectrum
            stored in 'self'

        See Also
        --------
        power_analyze

        """
        # check if the `spaces` input is valid
        spaces = utilities.cast_axis_to_tuple(spaces, len(self.domain))

        if spaces is None:
            spaces = range(len(self.domain))

        for power_space_index in spaces:
            power_space = self.domain[power_space_index]
            if not isinstance(power_space, PowerSpace):
                raise ValueError("A PowerSpace is needed for field "
                                 "synthetization.")

        # create the result domain
        result_domain = list(self.domain)
        for power_space_index in spaces:
            power_space = self.domain[power_space_index]
            harmonic_domain = power_space.harmonic_domain
            result_domain[power_space_index] = harmonic_domain

        # create random samples: one or two, depending on whether the
        # power spectrum is real or complex
        if real_power:
            result_list = [None]
        else:
            result_list = [None, None]

        result_list = [self.__class__.from_random(
                             'normal',
                             mean=mean,
                             std=std,
                             domain=result_domain,
                             dtype=np.complex,
                             distribution_strategy=self.distribution_strategy)
                       for x in result_list]

        # from now on extract the values from the random fields for further
        # processing without killing the fields.
        # if the signal-space field should be real, hermitianize the field
        # components

        spec = self.val.get_full_data()
        for power_space_index in spaces:
            spec = self._spec_to_rescaler(spec, result_list, power_space_index)
        local_rescaler = spec

        result_val_list = [x.val for x in result_list]

        # apply the rescaler to the random fields
        result_val_list[0].apply_scalar_function(
                                            lambda x: x * local_rescaler.real,
                                            inplace=True)

        if not real_power:
            result_val_list[1].apply_scalar_function(
                                            lambda x: x * local_rescaler.imag,
                                            inplace=True)

        if real_signal:
            for power_space_index in spaces:
                harmonic_domain = result_domain[power_space_index]
                result_val_list = [harmonic_domain.hermitian_decomposition(
                                    result_val,
                                    axes=result.domain_axes[power_space_index],
                                    preserve_gaussian_variance=True)[0]
                                   for (result, result_val)
                                   in zip(result_list, result_val_list)]

        # store the result into the fields
        [x.set_val(new_val=y, copy=False) for x, y in
            zip(result_list, result_val_list)]

        if real_power:
            result = result_list[0]
        else:
            result = result_list[0] + 1j*result_list[1]

        return result

    def _spec_to_rescaler(self, spec, result_list, power_space_index):
        power_space = self.domain[power_space_index]

        # weight the random fields with the power spectrum
        # therefore get the pindex from the power space
        pindex = power_space.pindex
        # take the local data from pindex. This data must be compatible to the
        # local data of the field given the slice of the PowerSpace
        local_distribution_strategy = \
            result_list[0].val.get_axes_local_distribution_strategy(
                result_list[0].domain_axes[power_space_index])

        if pindex.distribution_strategy is not local_distribution_strategy:
            self.logger.warn(
                "The distribution_stragey of pindex does not fit the "
                "slice_local distribution strategy of the synthesized field.")

        # Now use numpy advanced indexing in order to put the entries of the
        # power spectrum into the appropriate places of the pindex array.
        # Do this for every 'pindex-slice' in parallel using the 'slice(None)'s
        local_pindex = pindex.get_local_data(copy=False)

        local_blow_up = [slice(None)]*len(self.shape)
        local_blow_up[self.domain_axes[power_space_index][0]] = local_pindex
        # here, the power_spectrum is distributed into the new shape
        local_rescaler = spec[local_blow_up]
        return local_rescaler

    # ---Properties---

    def set_val(self, new_val=None, copy=False):
        """ Let's one set the values of the.

        Parameters
        ----------
        new_val : number, numpy.array, distributed_data_object,
                Field, None, *optional*
            The values to be stored in the field.
            {default : None}
                if new_val==None : sets the values to 0.

        copy : boolean, *optional*
            True if this field holds a copy of new_val, False if
            it holds the same object
            {default : False}
        See Also
        --------
        val

        """
        new_val = self.cast(new_val)
        if copy:
            new_val = new_val.copy()
        self._val = new_val
        return self

    def get_val(self, copy=False):
        """ Acceses the values stored in the Field.

        Parameters
        ----------
        copy : boolean
            True makes the method retrun a COPY of the Field's underlying
            distributed_data_object.

        Returns
        -------
        out : distributed_data_object
            The output object.

        See Also
        --------
        val

        """
        if self._val is None:
            self.set_val(None)

        if copy:
            return self._val.copy()
        else:
            return self._val

    @property
    def val(self):
        """ Retruns actual distributed_data_object associated with this Field.

        Returns
        -------
        out : distributed_data_object
            The output object.

        See Also
        --------
        get_val

        """
        return self.get_val(copy=False)

    @val.setter
    def val(self, new_val):
        """ Sets the values in the d2o of the Field.

        Parameters
        ----------
        new_val : number, numpy.array, distributed_data_object, Field
            If an array is provided it needs to have the same shape as the
            domain of the Field.

        See Also
        --------
        get_val

        """
        self.set_val(new_val=new_val, copy=False)

    @property
    def shape(self):
        """ Returns the shape of the Field/ it's domain.

        All axes lengths written down seperately in a tuple.

        Returns
        -------
        out : tuple
            The output object. The tuple contains the dimansions of the spaces
            in domain.

        See Also
        --------
        dim

        """
        shape_tuple = tuple(sp.shape for sp in self.domain)
        try:
            global_shape = reduce(lambda x, y: x + y, shape_tuple)
        except TypeError:
            global_shape = ()

        return global_shape

    @property
    def dim(self):
        """ Returns the dimension of the Field/it's domain.

        Multiplies all values from shape.

        Returns
        -------
        out : int
            The dimension of the Field.

        See Also
        --------
        shape

        """
        dim_tuple = tuple(sp.dim for sp in self.domain)
        try:
            return reduce(lambda x, y: x * y, dim_tuple)
        except TypeError:
            return 0

    @property
    def dof(self):
        dof = self.dim
        if issubclass(self.dtype.type, np.complexfloating):
            dof *= 2
        return dof

    @property
    def total_volume(self):
        volume_tuple = tuple(sp.total_volume for sp in self.domain)
        try:
            return reduce(lambda x, y: x * y, volume_tuple)
        except TypeError:
            return 0.

    # ---Special unary/binary operations---

    def cast(self, x=None, dtype=None):
        """ Transforms x to a d2o with the same shape as the domain of 'self'

        Parameters
        ----------
        x : number, d2o, Field, array_like
            The input that shall be casted on a d2o of the same shape like the
            domain.

        dtype : type
            The datatype the output shall have.

        Returns
        -------
        out : distributed_data_object
            The output object.

        See Also
        --------
        _actual_cast

        """
        if dtype is None:
            dtype = self.dtype
        else:
            dtype = np.dtype(dtype)

        casted_x = x

        for ind, sp in enumerate(self.domain):
            casted_x = sp.pre_cast(casted_x,
                                   axes=self.domain_axes[ind])

        casted_x = self._actual_cast(casted_x, dtype=dtype)

        for ind, sp in enumerate(self.domain):
            casted_x = sp.post_cast(casted_x,
                                    axes=self.domain_axes[ind])

        return casted_x

    def _actual_cast(self, x, dtype=None):
        if isinstance(x, Field):
            x = x.get_val()

        if dtype is None:
            dtype = self.dtype

        return_x = distributed_data_object(
                            global_shape=self.shape,
                            dtype=dtype,
                            distribution_strategy=self.distribution_strategy)
        return_x.set_full_data(x, copy=False)
        return return_x

    def copy(self, domain=None, dtype=None, distribution_strategy=None):
        """ Returns a full copy of the Field.

        If no keyword arguments are given, the returned object will be an
        identical copy of the original Field. By explicit specification one is
        able to define the domain, the dtype and the distribution_strategy of
        the returned Field.

        Parameters
        ----------
        domain : DomainObject
            The new domain the Field shall have.

        dtype : type
            The new dtype the Field shall have.

        distribution_strategy : all supported distribution strategies
            The new distribution strategy the Field shall have.

        Returns
        -------
        out : Field
            The output object. An identical copy of 'self'.

        See Also
        --------
        copy_empty

        """
        copied_val = self.get_val(copy=True)
        new_field = self.copy_empty(
                                domain=domain,
                                dtype=dtype,
                                distribution_strategy=distribution_strategy)
        new_field.set_val(new_val=copied_val, copy=False)
        return new_field

    def copy_empty(self, domain=None, dtype=None, distribution_strategy=None):
        """ Returns an empty copy of the Field.

        If no keyword arguments are given, the returned object will be an
        identical copy of the original Field containing random data. By
        explicit specification one is able to define the domain, the dtype and
        the distribution_strategy of the returned Field.

        Parameters
        ----------
        domain : DomainObject
            The new domain the Field shall have.

        dtype : type
            The new dtype the Field shall have.

        distribution_strategy : all supported distribution strategies
            The distribution strategy the new Field should have.

        Returns
        -------
        out : Field
            The output object. Contains random data.

        See Also
        --------
        copy
        _fast_copy_empty

        """
        if domain is None:
            domain = self.domain
        else:
            domain = self._parse_domain(domain)

        if dtype is None:
            dtype = self.dtype
        else:
            dtype = np.dtype(dtype)

        if distribution_strategy is None:
            distribution_strategy = self.distribution_strategy

        fast_copyable = True
        try:
            for i in xrange(len(self.domain)):
                if self.domain[i] is not domain[i]:
                    fast_copyable = False
                    break
        except IndexError:
            fast_copyable = False

        if (fast_copyable and dtype == self.dtype and
                distribution_strategy == self.distribution_strategy):
            new_field = self._fast_copy_empty()
        else:
            new_field = Field(domain=domain,
                              dtype=dtype,
                              distribution_strategy=distribution_strategy)
        return new_field

    def _fast_copy_empty(self):
        # make an empty field
        new_field = EmptyField()
        # repair its class
        new_field.__class__ = self.__class__
        # copy domain, codomain and val
        for key, value in self.__dict__.items():
            if key != '_val':
                new_field.__dict__[key] = value
            else:
                new_field.__dict__[key] = self.val.copy_empty()
        return new_field

    def weight(self, power=1, inplace=False, spaces=None):
        """ Devides every entry in 'self' by the dim of 'self'

        Parameters
        ----------
        power : number
            Here one can set the power to which the dimension is taken before
            division. power=2 will make the method devide every entry in 'self'
            by the square of the dimension.

        inplace : boolean
            For True the values in 'self' will be changed to the weighted ones.

        spaces : int
            Determines on what subspace the operation takes place.

        Returns
        -------
        out : Field
            The output object.

        """
        if inplace:
            new_field = self
        else:
            new_field = self.copy_empty()

        new_val = self.get_val(copy=False)

        spaces = utilities.cast_axis_to_tuple(spaces, len(self.domain))
        if spaces is None:
            spaces = range(len(self.domain))

        for ind, sp in enumerate(self.domain):
            if ind in spaces:
                new_val = sp.weight(new_val,
                                    power=power,
                                    axes=self.domain_axes[ind],
                                    inplace=inplace)

        new_field.set_val(new_val=new_val, copy=False)
        return new_field

    def dot(self, x=None, spaces=None, bare=False):
        """ Computes the dot product of 'self' with x.

        For a 1D Field this is the scalar product.

        Parameters
        ----------
        x : Field
            Must have the same shape as 'self'

        spaces : int


        bare : boolean
            bare=True operation will compute the sum over the pointwise product
            of 'self' and x.
            With bare=False this number will be devided by the dimension of the
            space over which the dotproduct is comupted.

        Returns
        -------
        out : float, complex

        """
        if not isinstance(x, Field):
            raise ValueError("The dot-partner must be an instance of " +
                             "the NIFTy field class")

        # Compute the dot respecting the fact of discrete/continuous spaces
        if bare:
            y = self
        else:
            y = self.weight(power=1)

        if spaces is None:
            x_val = x.get_val(copy=False)
            y_val = y.get_val(copy=False)
            result = (x_val.conjugate() * y_val).sum()
            return result
        else:
            # create a diagonal operator which is capable of taking care of the
            # axes-matching
            from nifty.operators.diagonal_operator import DiagonalOperator
            diagonal = y.val.conjugate()
            diagonalOperator = DiagonalOperator(domain=y.domain,
                                                diagonal=diagonal,
                                                copy=False)
            dotted = diagonalOperator(x, spaces=spaces)
            return dotted.sum(spaces=spaces)

    def norm(self, q=2):
        """ Computes the Lq-norm of the field values.

            Parameters
            ----------
            q : scalar
                Parameter q of the Lq-norm (default: 2).

            Returns
            -------
            norm : scalar
                The Lq-norm of the field values.

        """
        if q == 2:
            return (self.dot(x=self)) ** (1 / 2)
        else:
            return self.dot(x=self ** (q - 1)) ** (1 / q)

    def conjugate(self, inplace=False):
        """ Retruns the complex conjugate of the field.

        Parameters
        ----------
        inplace : boolean
            Decides whether self or a copied version of self shall be used

        Returns
        -------
        cc : field
            The complex conjugated field.

        """
        if inplace:
            work_field = self
        else:
            work_field = self.copy_empty()

        new_val = self.get_val(copy=False)
        new_val = new_val.conjugate()
        work_field.set_val(new_val=new_val, copy=False)

        return work_field

    # ---General unary/contraction methods---

    def __pos__(self):
        """ x.__pos__() <==> +x

        Returns a (positive) copy of `self`.
        """
        return self.copy()

    def __neg__(self):
        """ x.__neg__() <==> -x

        Returns a negative copy of `self`.
        """
        return_field = self.copy_empty()
        new_val = -self.get_val(copy=False)
        return_field.set_val(new_val, copy=False)
        return return_field

    def __abs__(self):
        """ x.__abs__() <==> abs(x)

        Returns an absolute valued copy of `self`.
        """
        return_field = self.copy_empty()
        new_val = abs(self.get_val(copy=False))
        return_field.set_val(new_val, copy=False)
        return return_field

    def _contraction_helper(self, op, spaces):
        # build a list of all axes
        if spaces is None:
            spaces = xrange(len(self.domain))
        else:
            spaces = utilities.cast_axis_to_tuple(spaces, len(self.domain))

        axes_list = tuple(self.domain_axes[sp_index] for sp_index in spaces)

        try:
            axes_list = reduce(lambda x, y: x+y, axes_list)
        except TypeError:
            axes_list = ()

        # perform the contraction on the d2o
        data = self.get_val(copy=False)
        data = getattr(data, op)(axis=axes_list)

        # check if the result is scalar or if a result_field must be constr.
        if np.isscalar(data):
            return data
        else:
            return_domain = tuple(self.domain[i]
                                  for i in xrange(len(self.domain))
                                  if i not in spaces)

            return_field = Field(domain=return_domain,
                                 val=data,
                                 copy=False)
            return return_field

    def sum(self, spaces=None):
        return self._contraction_helper('sum', spaces)

    def prod(self, spaces=None):
        return self._contraction_helper('prod', spaces)

    def all(self, spaces=None):
        return self._contraction_helper('all', spaces)

    def any(self, spaces=None):
        return self._contraction_helper('any', spaces)

    def min(self, spaces=None):
        return self._contraction_helper('min', spaces)

    def nanmin(self, spaces=None):
        return self._contraction_helper('nanmin', spaces)

    def max(self, spaces=None):
        return self._contraction_helper('max', spaces)

    def nanmax(self, spaces=None):
        return self._contraction_helper('nanmax', spaces)

    def mean(self, spaces=None):
        return self._contraction_helper('mean', spaces)

    def var(self, spaces=None):
        return self._contraction_helper('var', spaces)

    def std(self, spaces=None):
        return self._contraction_helper('std', spaces)

    # ---General binary methods---

    def _binary_helper(self, other, op, inplace=False):
        # if other is a field, make sure that the domains match
        if isinstance(other, Field):
            try:
                assert len(other.domain) == len(self.domain)
                for index in xrange(len(self.domain)):
                    assert other.domain[index] == self.domain[index]
            except AssertionError:
                raise ValueError(
                    "domains are incompatible.")
            other = other.get_val(copy=False)

        self_val = self.get_val(copy=False)
        return_val = getattr(self_val, op)(other)

        if inplace:
            working_field = self
        else:
            working_field = self.copy_empty(dtype=return_val.dtype)

        working_field.set_val(return_val, copy=False)
        return working_field

    def __add__(self, other):
        """ x.__add__(y) <==> x+y

        See Also
        --------
        _binary_helper
        """
        return self._binary_helper(other, op='__add__')

    def __radd__(self, other):
        """ x.__radd__(y) <==> y+x

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__radd__')

    def __iadd__(self, other):
        """ x.__iadd__(y) <==> x+=y

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__iadd__', inplace=True)

    def __sub__(self, other):
        """ x.__sub__(y) <==> x-y

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__sub__')

    def __rsub__(self, other):
        """ x.__rsub__(y) <==> y-x

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__rsub__')

    def __isub__(self, other):
        """ x.__isub__(y) <==> x-=y

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__isub__', inplace=True)

    def __mul__(self, other):
        """ x.__mul__(y) <==> x*y

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__mul__')

    def __rmul__(self, other):
        """ x.__rmul__(y) <==> y*x

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__rmul__')

    def __imul__(self, other):
        """ x.__imul__(y) <==> x*=y

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__imul__', inplace=True)

    def __div__(self, other):
        """ x.__div__(y) <==> x/y

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__div__')

    def __rdiv__(self, other):
        """ x.__rdiv__(y) <==> y/x

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__rdiv__')

    def __idiv__(self, other):
        """ x.__idiv__(y) <==> x/=y

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__idiv__', inplace=True)

    def __pow__(self, other):
        """ x.__pow__(y) <==> x**y

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__pow__')

    def __rpow__(self, other):
        """ x.__rpow__(y) <==> y**x

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__rpow__')

    def __ipow__(self, other):
        """ x.__ipow__(y) <==> x**=y

        See Also
        --------
        _builtin_helper
        """
        return self._binary_helper(other, op='__ipow__', inplace=True)

    def __lt__(self, other):
        """ x.__lt__(y) <==> x<y

        See Also
        --------
        _binary_helper
        """
        return self._binary_helper(other, op='__lt__')

    def __le__(self, other):
        """ x.__le__(y) <==> x<=y

        See Also
        --------
        _binary_helper
        """
        return self._binary_helper(other, op='__le__')

    def __ne__(self, other):
        """ x.__ne__(y) <==> x!=y

        See Also
        --------
        _binary_helper
        """
        if other is None:
            return True
        else:
            return self._binary_helper(other, op='__ne__')

    def __eq__(self, other):
        """ x.__eq__(y) <==> x=y

        See Also
        --------
        _binary_helper
        """
        if other is None:
            return False
        else:
            return self._binary_helper(other, op='__eq__')

    def __ge__(self, other):
        """ x.__ge__(y) <==> x>=y

        See Also
        --------
        _binary_helper
        """
        return self._binary_helper(other, op='__ge__')

    def __gt__(self, other):
        """ x.__gt__(y) <==> x>y

        See Also
        --------
        _binary_helper
        """
        return self._binary_helper(other, op='__gt__')

    def __repr__(self):
        """ Is called by jsut typing the instance's name.

        """
        return "<nifty_core.field>"

    def __str__(self):
        """ Is called by the print command.

        Retruns
        -------
        out : A sting with usefull information about the stored values and
            properties of 'self'

        """
        minmax = [self.min(), self.max()]
        mean = self.mean()
        return "nifty_core.field instance\n- domain      = " + \
               repr(self.domain) + \
               "\n- val         = " + repr(self.get_val()) + \
               "\n  - min.,max. = " + str(minmax) + \
               "\n  - mean = " + str(mean)

    # ---Serialization---

    def _to_hdf5(self, hdf5_group):
        hdf5_group.attrs['dtype'] = self.dtype.name
        hdf5_group.attrs['distribution_strategy'] = self.distribution_strategy
        hdf5_group.attrs['domain_axes'] = str(self.domain_axes)
        hdf5_group['num_domain'] = len(self.domain)

        if self._val is None:
            ret_dict = {}
        else:
            ret_dict = {'val': self.val}

        for i in range(len(self.domain)):
            ret_dict['s_' + str(i)] = self.domain[i]

        return ret_dict

    @classmethod
    def _from_hdf5(cls, hdf5_group, repository):
        # create empty field
        new_field = EmptyField()
        # reset class
        new_field.__class__ = cls
        # set values
        temp_domain = []
        for i in range(hdf5_group['num_domain'][()]):
            temp_domain.append(repository.get('s_' + str(i), hdf5_group))
        new_field.domain = tuple(temp_domain)

        exec('new_field.domain_axes = ' + hdf5_group.attrs['domain_axes'])

        try:
            new_field._val = repository.get('val', hdf5_group)
        except(KeyError):
            new_field._val = None

        new_field.dtype = np.dtype(hdf5_group.attrs['dtype'])
        new_field.distribution_strategy =\
            hdf5_group.attrs['distribution_strategy']

        return new_field


class EmptyField(Field):
    def __init__(self):
        pass
