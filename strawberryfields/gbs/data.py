# Copyright 2019 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""
GBS Datasets
============

**Module name:** :mod:`strawberryfields.gbs.data`

.. currentmodule:: strawberryfields.gbs.data

This module provides access to pre-calculated datasets of simulated GBS samples.

Graphs
------

We have generated datasets from a range of graphs, with each graph having a target application in
mind.

For dense subgraph and maximum clique identification, we provide:

.. autosummary::
    Planted
    TaceAs
    PHat

+---------------+---------------+
|   |planted|   |    |tace_as|  |
|               |               |
|  **Planted**  |   **TACE-AS** |
+---------------+---------------+

For graph similarity, we provide:

.. autosummary::
    Mutag0
    Mutag1
    Mutag2
    Mutag3

+-------------+-------------+
|  |mutag_0|  |  |mutag_1|  |
|             |             |
| **MUTAG_0** | **MUTAG_1** |
+-------------+-------------+
|  |mutag_2|  |  |mutag_3|  |
|             |             |
| **MUTAG_2** | **MUTAG_3** |
+-------------+-------------+

Molecules
---------

Using the :mod:`~.gbs.vibronic` module and :func:`~.gbs.sample.vibronic` function, GBS data has been
generated for formic acid at zero temperature. The GBS samples can be used to recover the
vibronic spectrum of the molecule.

.. autosummary::
    Formic

Dataset
-------

The :class:`Dataset` class provides the base functionality from which all datasets inherit.

.. autosummary::
    Dataset

Each dataset contains a variety of metadata relevant to the sampling:

- ``n_mean``: theoretical mean number of photons in the GBS device

-  ``threshold``: flag to indicate whether samples are generated with threshold detection or
   with photon-number-resolving detectors

- ``n_samples``: total number of samples in the dataset

- ``modes``: number of modes in the GBS device or, equivalently, number of nodes in the graph

- ``data``: the raw data accessible as a SciPy `csr sparse array
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csr_matrix.html>`__

Graph and molecule datasets also contain some specific data, such as the graph adjacency matrix
or the input molecular information.

.. autosummary::
    GraphDataset
    MoleculeDataset

Note that datasets are simulated without photon loss.

Loading data
------------

We use the :class:`Planted` class as an example to show how to interact with the datasets. Datasets
can be loaded by running:

>>> data = Planted()

Simply use indexing and slicing to access samples from the dataset:

>>> sample_3 = data[3]
>>> samples = data[:10]

Datasets also contain metadata relevant to the GBS setup:

>>> data.n_mean
8

>>> len(data)
50000

The number of photons or clicks in each sample is available using the :meth:`Dataset.counts` method:

>>> data.counts()
[2, 0, 8, 11, ... , 6]

For example, we see that the ``data[3]`` sample has 11 clicks.

Code details
^^^^^^^^^^^^
"""
# pylint: disable=unnecessary-pass
from abc import ABC, abstractmethod

import pkg_resources
import numpy as np
import scipy

DATA_PATH = pkg_resources.resource_filename("strawberryfields", "gbs/data") + "/"


class Dataset(ABC):
    """Base class for loading datasets of pre-generated samples.

    Attributes:
        n_mean (float): mean number of photons in the GBS device
        threshold (bool): flag to indicate whether samples are generated with threshold detection
            (i.e., detectors of zero or some photons) or with photon-number-resolving detectors.
        n_samples (int): total number of samples in the dataset
        modes (int): number of modes in the GBS device or, equivalently, number of nodes in graph
        data (sparse): raw data of samples from GBS as a `csr sparse array
            <https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.csr_matrix.html>`__.
    """

    _count = 0

    @property
    @abstractmethod
    def _data_filename(self) -> str:
        """Base name of files containing the sample data stored in the ``./data/`` directory.

        Samples and corresponding adjacency matrix should both be provided as a
        ``scipy.sparse.csr_matrix`` saved in ``.npz`` format.

        For ``_data_filename = "example"``, the corresponding samples should be stored as
        ``./data/example.npz`` and the adjacency matrix as ``./data/example_A.npz``."""
        pass

    def __init__(self):
        self.data = scipy.sparse.load_npz(DATA_PATH + self._data_filename + ".npz")
        self.n_samples, self.modes = self.data.shape

    def __iter__(self):
        return self

    def __next__(self):
        if self._count < self.n_samples:
            self._count += 1
            return self.__getitem__(self._count - 1)
        self._count = 0
        raise StopIteration

    def _elem(self, i):
        """Access the i-th element of the sparse array and output as a list."""
        return list(self.data[i].toarray()[0])

    def __getitem__(self, key):

        if not isinstance(key, (slice, tuple, int)):
            raise TypeError("Dataset indices must be integers, slices, or tuples")

        if isinstance(key, int):
            return self._elem(key + self.n_samples if key < 0 else key)

        if isinstance(key, tuple):
            key = slice(*key)

        range_tuple = key.indices(self.n_samples)
        return [self._elem(i) for i in range(*range_tuple)]

    def __len__(self):
        return self.n_samples

    def counts(self, axis: int = 1) -> list:
        """Count number of photons or clicks.

        Counts number of photons/clicks in each sample (``axis==1``) or number of photons/clicks
        in each mode compounded over all samples (``axis==0``).

        Args:
            axis (int): axis to perform count

        Returns:
            list: counts from samples
        """
        return np.array(self.data.sum(axis)).flatten().tolist()

    # pylint: disable=missing-docstring
    @property
    @abstractmethod
    def n_mean(self) -> float:
        pass

    # pylint: disable=missing-docstring
    @property
    @abstractmethod
    def threshold(self) -> bool:
        pass


# pylint: disable=abstract-method
class GraphDataset(Dataset, ABC):
    """Class for loading datasets of pre-generated samples from graphs.

    Attributes:
        adj (array): adjacency matrix of the graph from which samples were generated
    """

    def __init__(self):
        super().__init__()
        self.adj = scipy.sparse.load_npz(DATA_PATH + self._data_filename + "_A.npz").toarray()


class Planted(GraphDataset):
    """A random 30-node graph containing a dense 10-node subgraph planted inside
    :cite:`arrazola2018using`.

    The graph is generated by joining two Erdős–Rényi random graphs. The first 20-node graph is
    generated with edge probability of 0.5 and the second 10-node planted graph is generated with
    edge probability of 0.875. The two graphs are joined by selecting 8 vertices at random from
    both and adding an edge between them.

    The 10-node planted clique is contained within the final 10 nodes of the graph.

    **Graph:**

    .. |planted| image:: ../../_static/graphs/planted.png
        :align: middle
        :width: 250px
        :target: javascript:void(0);

    |planted|

    Attributes:
        n_mean = 8
        threshold = True
        n_samples = 50000
        modes = 30
    """

    _data_filename = "planted"
    n_mean = 8
    threshold = True


class TaceAs(GraphDataset):
    """Binding interaction graph for the TACE-AS complex :cite:`banchi2019molecular`.

    Nodes in this graph correspond to pairs of atoms in a target protein and a pharmaceutical
    molecule. Edges in the graph are added if the distance between both pairs of atoms is very
    close to equal. Cliques in the graph correspond to possible docking configurations of protein
    and molecule, and the largest clique is the most stable configuration. There are multiple
    maximum-sized cliques of 8 nodes in this graph.

    **Graph:**

    .. |tace_as| image:: ../../_static/graphs/TACE-AS.png
        :align: middle
        :width: 250px
        :target: javascript:void(0);

    |tace_as|

    Attributes:
        n_mean = 8
        threshold = True
        n_samples = 50000
        modes = 24
    """

    _data_filename = "TACE-AS"
    n_mean = 8
    threshold = True


class PHat(GraphDataset):
    """Random graph created using the p-hat generator of :cite:`gendreau1993solving`.

    This graph is the ``p_hat300-1`` graph of the `DIMACS
    <http://iridia.ulb.ac.be/~fmascia/maximum_clique/DIMACS-benchmark>`__ dataset, which is a
    collection of large graphs with cliques that are hard to find. The best known clique of
    this 300-node graph is of size 8 and is composed of nodes: ``[53, 123, 180, 218, 246, 267, 270,
    286]``. This graph is not visualized due to its large size.

    Attributes:
        n_mean = 10
        threshold = True
        n_samples = 50000
        modes = 300
    """

    _data_filename = "p_hat300-1"
    n_mean = 10
    threshold = True


class Mutag0(GraphDataset):
    """First graph of the MUTAG dataset.

    The MUTAG dataset is from :cite:`debnath1991structure,kriege2012subgraph` and is available
    `here <https://ls11-www.cs.tu-dortmund.de/staff/morris/graphkerneldatasets>`__.

    **Graph:**

    .. |mutag_0| image:: ../../_static/graphs/MUTAG_0.png
        :align: middle
        :width: 250px
        :target: javascript:void(0);

    |mutag_0|

    Attributes:
        n_mean = 6
        threshold = False
        n_samples = 20000
        modes = 17
    """

    _data_filename = "MUTAG_0"
    n_mean = 6
    threshold = False


class Mutag1(GraphDataset):
    """Second graph of the MUTAG dataset.

    The MUTAG dataset is from :cite:`debnath1991structure,kriege2012subgraph` and is available
    `here <https://ls11-www.cs.tu-dortmund.de/staff/morris/graphkerneldatasets>`__.

    **Graph:**

    .. |mutag_1| image:: ../../_static/graphs/MUTAG_1.png
        :align: middle
        :width: 250px
        :target: javascript:void(0);

    |mutag_1|

    Attributes:
        n_mean = 6
        threshold = False
        n_samples = 20000
        modes = 13
    """

    _data_filename = "MUTAG_1"
    n_mean = 6
    threshold = False


class Mutag2(GraphDataset):
    """Third graph of the MUTAG dataset.

    The MUTAG dataset is from :cite:`debnath1991structure,kriege2012subgraph` and is available
    `here <https://ls11-www.cs.tu-dortmund.de/staff/morris/graphkerneldatasets>`__.

    **Graph:**

    .. |mutag_2| image:: ../../_static/graphs/MUTAG_2.png
        :align: middle
        :width: 250px
        :target: javascript:void(0);

    |mutag_2|

    Attributes:
        n_mean = 6
        threshold = False
        n_samples = 20000
        modes = 13
    """

    _data_filename = "MUTAG_2"
    n_mean = 6
    threshold = False


class Mutag3(GraphDataset):
    """Fourth graph of the MUTAG dataset.

    The MUTAG dataset is from :cite:`debnath1991structure,kriege2012subgraph` and is available
    `here <https://ls11-www.cs.tu-dortmund.de/staff/morris/graphkerneldatasets>`__.

    **Graph:**

    .. |mutag_3| image:: ../../_static/graphs/MUTAG_3.png
        :align: middle
        :width: 250px
        :target: javascript:void(0);

    |mutag_3|

    Attributes:
        n_mean = 6
        threshold = False
        n_samples = 20000
        modes = 19
    """

    _data_filename = "MUTAG_3"
    n_mean = 6
    threshold = False


# pylint: disable=abstract-method
class MoleculeDataset(Dataset, ABC):
    r"""Class for loading datasets of pre-generated samples from molecules.

    Attributes:
        w (array): normal mode frequencies of the electronic ground state (:math:`\mbox{cm}^{-1}`)
        wp (array): normal mode frequencies of the electronic excited state (:math:`\mbox{cm}^{-1}`)
        Ud (array): Duschinsky matrix
        delta (array): Displacement vector, with entries :math:`delta_i=\sqrt{
        \omega_i/\hbar}d_i`, and :math:`d` is the Duschinsky displacement
        T (float): temperature (Kelvin)
    """

    def __init__(self):
        super().__init__()
        self.w = scipy.sparse.load_npz(DATA_PATH + self._data_filename + "_w.npz").toarray()[0]
        self.wp = scipy.sparse.load_npz(DATA_PATH + self._data_filename + "_wp.npz").toarray()[0]
        self.Ud = scipy.sparse.load_npz(DATA_PATH + self._data_filename + "_Ud.npz").toarray()
        self.delta = scipy.sparse.load_npz(DATA_PATH + self._data_filename + "_delta.npz").toarray(

        )[0]

    # pylint: disable=missing-docstring
    @property
    @abstractmethod
    def T(self) -> bool:
        pass


class Formic(MoleculeDataset):
    """Zero temperature formic acid.

    The molecular parameters are obtained from Ref. :cite:`huh2015boson`.

    **Molecule:**

    .. |formic| image:: ../../_static/formic.png
        :align: middle
        :width: 250px
        :target: javascript:void(0);

    |formic|

    Attributes:
        n_mean = 1.56
        threshold = False
        n_samples = 20000
        modes = 14
        T = 0
    """

    _data_filename = "formic"
    n_mean = 1.56
    threshold = False
    T = 0
