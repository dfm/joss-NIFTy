FROM ubuntu:latest

# dependencies via apt
RUN \
    apt-get update && \
    apt-get install -y build-essential python python-pip python-dev git \
    autoconf gsl-bin libgsl-dev openmpi-bin wget \
    libopenmpi-dev libatlas-base-dev libfftw3-bin libfftw3-dev \
    libfftw3-double3 libfftw3-long3 libfftw3-mpi-dev libfftw3-mpi3 \
    libfftw3-quad3 libfftw3-single3 libhdf5-10 libhdf5-dev \
    libhdf5-openmpi-10 libhdf5-openmpi-dev hdf5-tools \
	python-tk

# python dependencies
ADD ci/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade -r /tmp/requirements.txt

# install pyHealpix, pyfftw and h5py
ADD ci/install_pyHealpix.sh /tmp/install_pyHealpix.sh
RUN cd /tmp && chmod +x install_pyHealpix.sh && ./install_pyHealpix.sh
ADD ci/install_pyfftw.sh /tmp/install_pyfftw.sh
RUN cd /tmp && chmod +x install_pyfftw.sh && ./install_pyfftw.sh
ADD ci/install_h5py.sh /tmp/install_h5py.sh
RUN cd /tmp && chmod +x install_h5py.sh && ./install_h5py.sh

# copy sources and install nifty
COPY . /tmp/NIFTy
RUN pip install /tmp/NIFTy

# Cleanup
RUN rm -r /tmp/*
