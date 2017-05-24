import unittest

from numpy.testing import assert_approx_equal, assert_equal

from nifty import *

from itertools import product
from test.common import expand
from test.common import generate_spaces



class QuadraticPot(Energy):
    def __init__(self, position, N):
        super(QuadraticPot, self).__init__(position)
        self.N = N
        
    def at(self, position):
        return self.__class__(position, N = self.N)


    @property
    def value(self):
        H = 0.5 *self.position.dot(self.N.inverse_times(self.position))
        return H.real

    @property
    def gradient(self):
        g = self.N.inverse_times(self.position)
        return_g = g.copy_empty(dtype=np.float)
        return_g.val = g.val.real
        return return_g
            
    @property
    def curvature(self):
        return self.N



class VL_BFGS_Tests(unittest.TestCase):
    spaces = generate_spaces()


    @expand(product(spaces, [10,  100, 1000], [1E-3, 1E-4, 1E-5], [2, 3, 4] ))
    def test_property(self, space, iteration_limit, convergence_tolerance, 
                      convergence_level):
        
        x = Field.from_random('normal', domain=space)
        N = DiagonalOperator(space, diagonal = 1.)
        energy = QuadraticPot(position=x , N=N)
        
        minimizer = VL_BFGS(iteration_limit=iteration_limit,
                                    convergence_tolerance=convergence_tolerance, 
                                    convergence_level=convergence_level)
                                    
        (energy, convergence) = minimizer(energy)
        
        if energy.position.domain[0] != space:
            raise TypeError
        if type(convergence) != float:
            raise TypeError

    @expand(product(spaces, [10,  100, 1000], [1E-3, 1E-4, 1E-5], [2, 3, 4] ))
    def test_property(self, space, iteration_limit, convergence_tolerance, 
                      convergence_level):
        
        x = Field.from_random('normal', domain=space)
        test_x = Field(space, val = 0.)
        N = DiagonalOperator(space, diagonal = 1.)
        energy = QuadraticPot(position=x , N=N)
        
        minimizer = VL_BFGS(iteration_limit=iteration_limit,
                                    convergence_tolerance=convergence_tolerance, 
                                    convergence_level=convergence_level)
                                    
        (energy, convergence) = minimizer(energy)
        
        assert_approx_equal(energy.value, 0, significant=3)
        assert_approx_equal(energy.position.val.get_full_data(), 
                            test_x.val.get_full_data(), significant=3)
        assert_equal(convergence, convergence_level)

