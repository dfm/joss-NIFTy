# -*- coding: utf-8 -*-

import abc

import numpy as np

from nifty.field_types import FieldType
from nifty.spaces import Space
from nifty.field import Field

from d2o import STRATEGIES as DISTRIBUTION_STRATEGIES


class Prober(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, domain=None, field_type=None,
                 distribution_strategy=None, probe_count=8,
                 random_type='pm1', compute_variance=False):

        self.domain = domain
        self.field_type = field_type
        self.distribution_strategy = distribution_strategy
        self.probe_count = probe_count
        self.random_type = random_type
        self.compute_variance = bool(compute_variance)

    def _parse_domain(self, domain):
        if domain is None:
            domain = ()
        elif isinstance(domain, Space):
            domain = (domain,)
        elif not isinstance(domain, tuple):
            domain = tuple(domain)

        for d in domain:
            if not isinstance(d, Space):
                raise TypeError(
                    "Given object contains something that is not a "
                    "nifty.space.")
        return domain

    def _parse_field_type(self, field_type):
        if field_type is None:
            field_type = ()
        elif isinstance(field_type, FieldType):
            field_type = (field_type,)
        elif not isinstance(field_type, tuple):
            field_type = tuple(field_type)

        for ft in field_type:
            if not isinstance(ft, FieldType):
                raise TypeError(
                    "Given object is not a nifty.FieldType.")
        return field_type

    # ---Properties---

    @property
    def domain(self):
        return self._domain

    @domain.setter
    def domain(self, domain):
        self._domain = self._parse_domain(domain)

    @property
    def field_type(self):
        return self._field_type

    @field_type.setter
    def field_type(self, field_type):
        self._field_type = self._parse_field_type(field_type)

    @property
    def distribution_strategy(self):
        return self._distribution_strategy

    @distribution_strategy.setter
    def distribution_strategy(self, distribution_strategy):
        distribution_strategy = str(distribution_strategy)
        if distribution_strategy not in DISTRIBUTION_STRATEGIES['global']:
            raise ValueError("distribution_strategy must be a global-type "
                             "strategy.")
        self._distribution_strategy = distribution_strategy

    @property
    def probe_count(self):
        return self._probe_count

    @probe_count.setter
    def probe_count(self, probe_count):
        self._probe_count = int(probe_count)

    @property
    def random_type(self):
        return self._random_type

    @random_type.setter
    def random_type(self, random_type):
        if random_type not in ["pm1", "normal"]:
            raise ValueError(
                "unsupported random type: '" + str(random_type) + "'.")
        else:
            self._random_type = random_type

    # ---Probing methods---

    def probing_run(self, callee):
        """ controls the generation, evaluation and finalization of probes """
        sum_of_probes = 0
        sum_of_squares = 0

        for index in xrange(self.probe_count):
            current_probe = self.get_probe(index)
            pre_result = self.process_probe(callee, current_probe, index)
            result = self.finish_probe(current_probe, pre_result)

            sum_of_probes += result
            if self.compute_variance:
                sum_of_squares += result.conjugate() * result

        mean_and_variance = self.finalize(sum_of_probes, sum_of_squares)
        return mean_and_variance

    def get_probe(self, index):
        """ layer of abstraction for potential probe-caching """
        return self.generate_probe()

    def generate_probe(self):
        """ a random-probe generator """
        f = Field.from_random(random_type=self.random_type,
                              domain=self.domain,
                              field_type=self.field_type,
                              distribution_strategy=self.distribution_strategy)
        uid = np.random.randint(1e18)
        return (uid, f)

    def process_probe(self, callee, probe, index):
        """ layer of abstraction for potential result-caching/recycling """
        return self.evaluate_probe(callee, probe[1])

    def evaluate_probe(self, callee, probe, **kwargs):
        """ processes a probe """
        return callee(probe, **kwargs)

    @abc.abstractmethod
    def finish_probe(self, probe, pre_result):
        return pre_result

    def finalize(self, sum_of_probes, sum_of_squares):
        probe_count = self.probe_count
        mean_of_probes = sum_of_probes/probe_count
        if self.compute_variance:
            # variance = 1/(n-1) (sum(x^2) - 1/n*sum(x)^2)
            variance = ((sum_of_squares - sum_of_probes*mean_of_probes) /
                        (probe_count-1))
        else:
            variance = None

        return (mean_of_probes, variance)

    def __call__(self, callee):
        return self.probing_run(callee)
