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


class TraceProberMixin(object):
    def __init__(self, *args, **kwargs):
        self.reset()
        super(TraceProberMixin, self).__init__(*args, **kwargs)

    def reset(self):
        self.__sum_of_probings = 0
        self.__sum_of_squares = 0
        self.__trace = None
        self.__trace_variance = None
        super(TraceProberMixin, self).reset()

    def finish_probe(self, probe, pre_result):
        result = probe[1].dot(pre_result, bare=True)
        self.__sum_of_probings += result
        if self.compute_variance:
            self.__sum_of_squares += result.conjugate() * result
        super(TraceProberMixin, self).finish_probe(probe, pre_result)

    @property
    def trace(self):
        if self.__trace is None:
            self.__trace = self.__sum_of_probings/self.probe_count
        return self.__trace

    @property
    def trace_variance(self):
        if not self.compute_variance:
            raise AttributeError("self.compute_variance is set to False")
        if self.__trace_variance is None:
            # variance = 1/(n-1) (sum(x^2) - 1/n*sum(x)^2)
            n = self.probe_count
            sum_pr = self.__sum_of_probings
            mean = self.trace
            sum_sq = self.__sum_of_squares

            self.__trace_variance = ((sum_sq - sum_pr*mean) / (n-1))
        return self.__trace_variance
