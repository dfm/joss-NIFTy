# -*- coding: utf-8 -*-

from numpy.testing import assert_equal, \
    assert_almost_equal, \
    assert_raises

from nose_parameterized import parameterized
import unittest
import itertools
import numpy as np

from d2o import distributed_data_object

from nifty import Space, \
    point_space

from nifty.rg import RGSpace

from nifty.lm import *

from nifty.field import Field

from nifty.nifty_core import POINT_DISTRIBUTION_STRATEGIES
from nifty.rg.rg_space import RG_DISTRIBUTION_STRATEGIES, \
    gc as RG_GC
from nifty.lm.nifty_lm import LM_DISTRIBUTION_STRATEGIES, \
    GL_DISTRIBUTION_STRATEGIES, \
    HP_DISTRIBUTION_STRATEGIES


###############################################################################

def custom_name_func(testcase_func, param_num, param):
    return "%s_%s" % (
        testcase_func.__name__,
        parameterized.to_safe_name("_".join(str(x) for x in param.args)),
    )


###############################################################################
###############################################################################

all_point_datatypes = [np.dtype('bool'),
                       np.dtype('int16'),
                       np.dtype('int32'),
                       np.dtype('int64'),
                       np.dtype('float32'),
                       np.dtype('float64'),
                       np.dtype('complex64'),
                       np.dtype('complex128')]

all_lm_datatypes = [np.dtype('complex64'),
                    np.dtype('complex128')]

all_gl_datatypes = [np.dtype('float64'),
                    np.dtype('float128')]

all_hp_datatypes = [np.dtype('float64')]

###############################################################################

DATAMODELS = {}
DATAMODELS['point_space'] = POINT_DISTRIBUTION_STRATEGIES
DATAMODELS['rg_space'] = RG_DISTRIBUTION_STRATEGIES
DATAMODELS['lm_space'] = LM_DISTRIBUTION_STRATEGIES
DATAMODELS['gl_space'] = GL_DISTRIBUTION_STRATEGIES
DATAMODELS['hp_space'] = HP_DISTRIBUTION_STRATEGIES

###############################################################################

fft_modules = []
for name in ['gfft', 'gfft_dummy', 'pyfftw']:
    if RG_GC.validQ('fft_module', name):
        fft_modules += [name]

###############################################################################

point_like_spaces = ['point_space', 'rg_space', 'lm_space', 'hp_space',
                     'gl_space']

###############################################################################

space_list = []

# Add point_spaces
for param in itertools.product([1, 10],
                               all_point_datatypes):
    space_list += [[point_space(num=param[0], dtype=param[1])]]

# Add rg_spaces
for param in itertools.product([(1,), (4, 6), (5, 8)],
                               [False, True],
                               [0, 1, 2],
                               [None, 0.3],
                               [False],
                               DATAMODELS['rg_space'],
                               fft_modules):
    space_list += [[RGSpace(shape=param[0],
                             zerocenter=param[1],
                             complexity=param[2],
                             distances=param[3],
                             harmonic=param[4],
                             fft_module=param[6]), param[5]]]


def generate_space_with_size(name, num):
    space_dict = {'space': Space(),
                  'point_space': point_space(num),
                  'rg_space': RGSpace((num, num)),
                  'lm_space': LMSpace(mmax=num+1, lmax=num+1),
                  'hp_space': HPSpace(num),
                  'gl_space': GLSpace(nlat=num, nlon=2*num-1),
                  }
    return space_dict[name]


def generate_data(space):
    a = np.arange(space.dim).reshape(space.shape)
    return distributed_data_object(a)


###############################################################################
###############################################################################

class Test_field_init(unittest.TestCase):
    @parameterized.expand(
        itertools.product([(1,), (4, 6), (5, 8)],
                          [False, True],
                          [0, 1, 2],
                          [None, 0.3],
                          [False],
                          fft_modules,
                          DATAMODELS['rg_space']),
        testcase_func_name=custom_name_func)
    def test_successfull_init_and_attributes(self, shape, zerocenter,
                                             complexity, distances, harmonic,
                                             fft_module, datamodel):
        s = RGSpace(shape=shape, zerocenter=zerocenter,
                     complexity=complexity, distances=distances,
                     harmonic=harmonic, fft_module=fft_module)
        f = Field(domain=(s,), dtype=s.dtype, datamodel=datamodel)
        assert (f.domain[0] is s)
        assert (s.check_codomain(f.codomain[0]))
        assert (s.shape == f.shape)


class Test_field_init2(unittest.TestCase):
    @parameterized.expand(
        itertools.product(point_like_spaces, [4],
                          DATAMODELS['rg_space']),
        testcase_func_name=custom_name_func)
    def test_successfull_init_and_attributes(self, name, num, datamodel):
        s = generate_space_with_size(name, num)
        d = generate_data(s)
        f = Field(val=d, domain=(s,), dtype=s.dtype, datamodel=datamodel)
        assert (f.domain[0] is s)
        assert (s.check_codomain(f.codomain[0]))
        assert (s.shape == f.shape)


class Test_field_multiple_rg_init(unittest.TestCase):
    @parameterized.expand(
        itertools.product([(1,)],
                          [True],
                          [0],
                          [None],
                          [False],
                          fft_modules,
                          DATAMODELS['rg_space']),
        testcase_func_name=custom_name_func)
    def test_multiple_space_init(self, shape, zerocenter,
                                 complexity, distances, harmonic,
                                 fft_module, datamodel):
        s1 = RGSpace(shape=shape, zerocenter=zerocenter,
                      complexity=complexity, distances=distances,
                      harmonic=harmonic, fft_module=fft_module)
        s2 = RGSpace(shape=shape, zerocenter=zerocenter,
                      complexity=complexity, distances=distances,
                      harmonic=harmonic, fft_module=fft_module)
        f = Field(domain=(s1, s2), dtype=s1.dtype, datamodel=datamodel)
        assert (f.domain[0] is s1)
        assert (f.domain[1] is s2)
        assert (s1.check_codomain(f.codomain[0]))
        assert (s2.check_codomain(f.codomain[1]))
        assert (s1.shape + s2.shape == f.shape)


class Test_field_multiple_init(unittest.TestCase):
    @parameterized.expand(
        itertools.product(point_like_spaces, point_like_spaces, [4]),
        testcase_func_name=custom_name_func)
    def test_multiple_space_init(self, space1, space2, shape):
        s1 = generate_space_with_size(space1, shape)
        s2 = generate_space_with_size(space2, shape)
        f = Field(domain=(s1, s2))
        assert (f.domain[0] is s1)
        assert (f.domain[1] is s2)
        assert (s1.check_codomain(f.codomain[0]))
        assert (s2.check_codomain(f.codomain[1]))
        assert (s1.shape + s2.shape == f.shape)
        s3 = generate_space_with_size('hp_space', shape)
        f = Field(domain=(s1, s2, s3))
        assert (f.domain[0] is s1)
        assert (f.domain[1] is s2)
        assert (f.domain[2] is s3)
        assert (s1.check_codomain(f.codomain[0]))
        assert (s2.check_codomain(f.codomain[1]))
        assert (s3.check_codomain(f.codomain[2]))
        assert (s1.shape + s2.shape + s3.shape ==
                f.shape)


class Test_axis(unittest.TestCase):
    @parameterized.expand(
        itertools.product(point_like_spaces, [4],
                          ['sum', 'prod', 'mean', 'var', 'std', 'median', 'all',
                           'any', 'min', 'nanmin', 'argmin', 'max', 'nanmax',
                           'argmax'],
                          [None, (0,)],
                          DATAMODELS['rg_space']),
        testcase_func_name=custom_name_func)
    def test_unary_operations(self, name, num, op, axis, datamodel):
        s = generate_space_with_size(name, num)
        d = generate_data(s)
        a = d.get_full_data()
        f = Field(val=d, domain=(s,), dtype=s.dtype, datamodel=datamodel)
        if op in ['argmin', 'argmax']:
            assert_almost_equal(getattr(f, op)(),
                                getattr(np, op)(a), decimal=4)
        else:
            assert_almost_equal(getattr(f, op)(axis=axis),
                                getattr(np, op)(a, axis=axis), decimal=4)


binary_operations = [('add','__add__'),('radd','__radd__'),('iadd','__iadd__'),
                     ('sub','__sub__'),('rsub','__rsub__'),('isub','__isub__'),
                     ('mul','__mul__'),('rmul','__rmul__'),('imul','__imul__'),
                     ('div','__div__'),('rdiv','__rdiv__'),('idiv','__idiv__'),
                     ('pow','__pow__'),('rpow','__rpow__'),('ipow','__ipow__'),
                     ('ne','__ne__'),('lt','__lt__'),('eq','__eq__'),
                     ('ge','__ge__'),('gt','__gt__')]

class Test_binary_operation(unittest.TestCase):
    @parameterized.expand(
    itertools.product([point_like_spaces[0]], [4], binary_operations,
                      DATAMODELS['rg_space']),
    testcase_func_name=custom_name_func)
    def test_binary_operations(self, name, num, op, datamodel):
        s = generate_space_with_size(name, num)
        d = generate_data(s)
        a = d.get_full_data()
        f = Field(val=d, domain=(s,), dtype=s.dtype, datamodel=datamodel)
        d2 = d[::-1]
        a2 = np.copy(a[::-1])
        if op[0] in ['iadd','isub','imul','idiv']:
            getattr(a, op[1])(a2)
            f.binary_operation(d, d2, op[0])
            assert_almost_equal(a,d,4)
        else:
            assert_almost_equal(getattr(a, op[1])(a2),f.binary_operation(d, d2,
                                                                      op[0]), 4)