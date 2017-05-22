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

import abc

from nifty.domain_object import DomainObject


class Space(DomainObject):
    """ The abstract base class for all NIFTy spaces.

    An instance of a space contains information about the manifolds
    geometry and enhances the functionality of DomainObject by methods that
    are needed for powerspectrum analysis and smoothing.

    Parameters
    ----------
    None

    Attributes
    ----------
    dim : np.int
        Total number of dimensionality, i.e. the number of pixels.
    harmonic : bool
        Specifies whether the space is a signal or harmonic space.
    total_volume : np.float
        The total volume of the space.
    shape : tuple of np.ints
        The shape of the space's data array.

    Raises
    ------
    TypeError
        Raised if instantiated directly.

    Notes
    -----
    `Space` is an abstract base class. In order to allow for instantiation
    the methods `get_distance_array`, `total_volume` and `copy` must be
    implemented as well as the abstract methods inherited from
    `DomainObject`.

    """

    def __init__(self):

        super(Space, self).__init__()

    @abc.abstractproperty
    def harmonic(self):
        """ Returns True if this space is a harmonic space.

        Raises
        ------
        NotImplementedError
            If called for this abstract class.

        """

        raise NotImplementedError

    @abc.abstractproperty
    def total_volume(self):
        """ Returns the total volume of the space.

        Returns
        -------
        float
            A real number representing the sum of all pixel volumes.

        Raises
        ------
        NotImplementedError
            If called for this abstract class.

        """
        raise NotImplementedError(
            "There is no generic volume for the Space base class.")

    @abc.abstractmethod
    def copy(self):
        """ Returns a copy of this Space instance.

        Returns
        -------
        Space
            A copy of this instance.

        """

        return self.__class__()

    def get_distance_array(self, distribution_strategy):
        """ The distances of the pixel to zero.

        This returns an array that gives for each pixel its distance to the
        center of the manifolds grid.

        Parameters
        ----------
        distribution_strategy : str
            The distribution_strategy which shall be used the returned
            distributed_data_object.

        Returns
        -------
        distributed_data_object
            A d2o containing the distances

        Raises
        ------
        NotImplementedError
            If called for this abstract class.

        """

        raise NotImplementedError(
            "There is no generic distance structure for Space base class.")

    def get_fft_smoothing_kernel_function(self, sigma):
        """ This method returns a smoothing kernel function.

        This method, which is only implemented for harmonic spaces, helps
        smoothing fields that live in a position space that has this space as
        its harmonic space. The returned function multiplies field values of a
        field with a zero centered Gaussian which corresponds to a convolution
        with a Gaussian kernel and sigma standard deviation in position space.

        Parameters
        ----------
        sigma : float
            A real number representing a physical scale on which the smoothing
            takes place. The smoothing is defined with respect to the real
            physical field and points that are closer together than one sigma
            are blurred together. Mathematically sigma is the standard
            deviation of a convolution with a normalized, zero-centered
            Gaussian that takes place in position space.

        Returns
        -------
        function (array-like -> array-like)
            A smoothing operation that multiplies values with a Gaussian
            kernel.

        Raises
        ------
        NotImplementedError :
            If called for this abstract class.

        """

        raise NotImplementedError(
            "There is no generic co-smoothing kernel for Space base class.")

    def hermitian_decomposition(self, x, axes,
                                preserve_gaussian_variance=False):
        """ Decomposes x into its hermitian and anti-hermitian constituents.

        This method decomposes a field's array x into its hermitian and
        antihermitian part, which corresponds to  real and imaginary part
        in a corresponding harmonic partner space. This is an internal function
        that is mainly used for power-synthesizing and -analyzing Fields.

        Parameters
        ----------
        x : distributed_data_object
            The field's val object.
        axes : tuple of ints
            Specifies the axes of x which correspond to this space.

        preserve_gaussian_variance : bool *optional*
            FIXME: figure out what this does

        Returns
        -------
        (distributed_data_object, distributed_data_object)
            A tuple of two distributed_data_objects, the first being the
            hermitian and the second the anti-hermitian part of x.

        Raises
        ------
        NotImplementedError
            If called for this abstract class.

        """

        raise NotImplementedError

    def __repr__(self):
        return str(type(self)) + "\n"
