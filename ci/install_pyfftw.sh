#!/bin/bash

git clone -b mpi https://github.com/fredros/pyFFTW.git
cd pyFFTW/
CC=mpicc python setup.py build_ext install
cd ..
rm -r pyFFTW
