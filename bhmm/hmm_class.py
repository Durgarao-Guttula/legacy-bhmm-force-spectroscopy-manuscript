"""
Hidden Markov model representation.

"""

import numpy as np
import output_models

__author__ = "John D. Chodera, Frank Noe"
__copyright__ = "Copyright 2015, John D. Chodera and Frank Noe"
__credits__ = ["John D. Chodera", "Frank Noe"]
__license__ = "LGPL"
__maintainer__ = "John D. Chodera"
__email__="jchodera AT gmail DOT com"

class HMM(object):
    """
    Hidden Markov model (HMM).

    This class is used to represent an HMM. This could be a maximum-likelihood HMM or a sampled HMM from a Bayesian posterior.

    Parameters
    ----------
    nstates : int
        The number of hidden states.
    Tij : np.array with shape (nstates, nstates), optional, default=None
        Row-stochastic transition matrix among states.
    output_model : bhmm.OutputModel
        The output model for the states.
    lag : int, optional, default=1
        Lag time (optional). Used to compute relaxation timescales.
    Pi : np.array with shape (nstates), optional, default=None
        The initial state vector. Required when stationary=False
    stationary : bool, optional, default=True
        If true, the initial distribution is equal to the stationary distribution of the transition matrix
        If false, the initial distribution must be given as Pi
    reversible : bool, optional, default=True
        If true, the transition matrix is reversible.

    Examples
    --------

    >>> # Gaussian HMM
    >>> nstates = 2
    >>> Tij = np.array([[0.8, 0.2], [0.5, 0.5]])
    >>> from output_models import GaussianOutputModel
    >>> output_model = GaussianOutputModel(nstates, means=[-1, +1], sigmas=[1, 1])
    >>> model = HMM(nstates, Tij, output_model)

    >>> # Discrete HMM
    >>> nstates = 2
    >>> Tij = np.array([[0.8, 0.2], [0.5, 0.5]])
    >>> from output_models import DiscreteOutputModel
    >>> output_model = DiscreteOutputModel([[0.5, 0.1, 0.4], [0.2, 0.3, 0.5]])
    >>> model = HMM(nstates, Tij, output_model)

    """
    def __init__(self, Tij, output_model, lag=1, Pi=None, stationary=True, reversible=True):
        # TODO: Perform sanity checks on data consistency.
        # EMMA imports
        from pyemma.msm import analysis as msmana

        # save a copy of the transition matrix
        self._Tij = np.array(Tij)
        assert msmana.is_transition_matrix(self._Tij), 'Given transition matrix is not a stochastic matrix'
        # set number of states
        self._nstates = self._Tij.shape[0]
        # lag time
        self._lag = lag
        # output model
        self.output_model = output_model
        # hidden state trajectories are optional
        self.hidden_state_trajectories = None

        # initial / stationary distribution
        if (Pi is not None):
            assert np.all(Pi >= 0), 'Given initial distribution contains negative elements.'
            Pi = np.array(Pi) / np.sum(Pi) # ensure normalization and make a copy

        self._stationary = stationary
        if (stationary):
            pT = msmana.stationary_distribution(self._Tij)
            if Pi is None: # stationary and no stationary distribution fixed, so computing it from trans. mat.
                self._Pi = pT
            else: # stationary but stationary distribution is fixed, so the transition matrix must be consistent
                assert np.allclose(Pi, pT), 'Stationary HMM requested, but given distribution is not the ' \
                                            'stationary distribution of the given transition matrix.'
                self._Pi = Pi
        else:
            if Pi is None: # no initial distribution given, so use stationary distribution anyway
                self._Pi = msmana.stationary_distribution(self._Tij)
            else:
                self._Pi = Pi

        # reversible
        self._reversible = reversible
        if reversible:
            assert msmana.is_reversible(Tij), 'Reversible HMM requested, but given transition matrix is not reversible.'

        # do eigendecomposition by default, because it's very cheap for hidden transition matrices
        if self._reversible:
            self._R, self._D, self._L = msmana.rdl_decomposition(self._Tij, norm='reversible')
            # everything must be real-valued
            self._R = self._R.real
            self._D = self._D.real
            self._L = self._L.real
        else:
            self._R, self._D, self._L = msmana.rdl_decomposition(self._Tij, norm='standard')
        self._eigenvalues = np.diag(self._D)


    def __repr__(self):
        return "HMM(%d, %s, %s, Pi=%s, stationary=%s, reversible=%s)" % (self._nstates,
                                                                         repr(self._Tij),
                                                                         repr(self.output_model),
                                                                         repr(self._Pi),
                                                                         repr(self._stationary),
                                                                         repr(self._reversible))

    def __str__(self):
        output  = 'Hidden Markov model\n'
        output += '-------------------\n'
        output += 'nstates: %d\n' % self._nstates
        output += 'Tij:\n'
        output += str(self._Tij) + '\n'
        output += 'Pi:\n'
        output += str(self._Pi) + '\n'
        output += 'output model:\n'
        output += str(self.output_model)
        output += '\n'
        return output

    # @property
    # def logPi(self):
    #     return np.log(self._Pi)
    #
    # @property
    # def logTij(self):
    #     return np.log(self._Tij)

    @property
    def is_reversible(self):
        return self._reversible

    @property
    def is_stationary(self):
        return self._stationary

    @property
    def nstates(self):
        return self._nstates

    @property
    def initial_distribution(self):
        return self._Pi

    @property
    def stationary_distribution(self):
        if self._stationary:
            return self._Pi
        else:
            raise ValueError('HMM is not stationary')

    @property
    def transition_matrix(self):
        return self._Tij

    @property
    def eigenvalues(self):
        """Transition matrix eigenvalues

        Returns
        -------
        ts : ndarray(m)
            transition matrix eigenvalues :math:`\lambda_i, i = 1,...,k`., sorted by descending norm.

        """
        return self._eigenvalues

    @property
    def eigenvectors_left(self):
        """Left transition matrix eigenvectors

        Returns
        -------
        L : ndarray(nstates,nstates)
            left eigenvectors in a row matrix. l_ij is the j'th component of the i'th left eigenvector

        """
        return self._L

    def eigenvectors_right(self):
        """Right transition matrix eigenvectors

        Returns
        -------
        R : ndarray(nstates,nstates)
            right eigenvectors in a column matrix. r_ij is the i'th component of the j'th right eigenvector

        """
        return self._R

    def timescales(self):
        """
        The relaxation timescales corresponding to the eigenvalues

        Returns
        -------
        ts : ndarray(m)
            relaxation timescales in units of the input trajectory time step,
            defined by :math:`-tau / ln | \lambda_i |, i = 2,...,nstates`.

        """
        from pyemma.msm.analysis.dense.decomposition import timescales_from_eigenvalues as _timescales

        ts = _timescales(self._eigenvalues, tau=self._lag)
        return ts[1:]

    def count_matrix(self, dtype=np.float64):
        """Compute the transition count matrix from hidden state trajectory.

        Parameters
        ----------
        dtype : numpy.dtype, optional, default=numpy.float64
            The numpy dtype to use for the count matrix.

        Returns
        -------
        C : numpy.array with shape (nstates,nstates)
            C[i,j] is the number of transitions observed from state i to state j

        Raises
        ------
        RuntimeError
            A RuntimeError is raised if the HMM model does not yet have a hidden state trajectory associated with it.

        Examples
        --------

        """

        if self.hidden_state_trajectories is None:
            raise RuntimeError('HMM model does not have a hidden state trajectory.')

        C = np.zeros((self._nstates,self._nstates), dtype=dtype)
        for S in self.hidden_state_trajectories:
            for t in range(len(S)-1):
                C[S[t],S[t+1]] += 1
        return C

    # def emission_probability(self, state, observation):
    #     """Compute the emission probability of an observation from a given state.
    #
    #     Parameters
    #     ----------
    #     state : int
    #         The state index for which the emission probability is to be computed.
    #
    #     Returns
    #     -------
    #     Pobs : float
    #         The probability (or probability density, if continuous) of the observation.
    #
    #     TODO
    #     ----
    #     * Vectorize
    #
    #     Examples
    #     --------
    #
    #     Compute the probability of observing an emission of 0 from state 0.
    #
    #     >>> from bhmm import testsystems
    #     >>> model = testsystems.dalton_model(nstates=3)
    #     >>> state_index = 0
    #     >>> observation = 0.0
    #     >>> Pobs = model.emission_probability(state_index, observation)
    #
    #     """
    #     return self.output_model.p_o_i(observation, state)

    # def log_emission_probability(self, state, observation):
    #     """Compute the log emission probability of an observation from a given state.
    #
    #     Parameters
    #     ----------
    #     state : int
    #         The state index for which the emission probability is to be computed.
    #
    #     Returns
    #     -------
    #     log_Pobs : float
    #         The log probability (or probability density, if continuous) of the observation.
    #
    #     TODO
    #     ----
    #     * Vectorize
    #
    #     Examples
    #     --------
    #
    #     Compute the log probability of observing an emission of 0 from state 0.
    #
    #     >>> from bhmm import testsystems
    #     >>> model = testsystems.dalton_model(nstates=3)
    #     >>> state_index = 0
    #     >>> observation = 0.0
    #     >>> log_Pobs = model.log_emission_probability(state_index, observation)
    #
    #     """
    #     return self.output_model.log_p_o_i(observation, state)

    def collect_observations_in_state(self, observations, state_index):
        """Collect a vector of all observations belonging to a specified hidden state.

        Parameters
        ----------
        observations : list of numpy.array
            List of observed trajectories.
        state_index : int
            The index of the hidden state for which corresponding observations are to be retrieved.
        dtype : numpy.dtype, optional, default=numpy.float64
            The numpy dtype to use to store the collected observations.

        Returns
        -------
        collected_observations : numpy.array with shape (nsamples,)
            The collected vector of observations belonging to the specified hidden state.

        Raises
        ------
        RuntimeError
            A RuntimeError is raised if the HMM model does not yet have a hidden state trajectory associated with it.

        """
        if not self.hidden_state_trajectories:
            raise RuntimeError('HMM model does not have a hidden state trajectory.')

        dtype = observations[0].dtype
        collected_observations = np.array([], dtype=dtype)
        for (s_t, o_t) in zip(self.hidden_state_trajectories, observations):
            indices = np.where(s_t == state_index)[0]
            collected_observations = np.append(collected_observations, o_t[indices])

        return collected_observations

    def generate_synthetic_state_trajectory(self, length, initial_Pi=None, dtype=np.int32):
        """Generate a synthetic state trajectory.

        Parameters
        ----------
        length : int
            Length of synthetic state trajectory to be generated.
        initial_Pi : np.array of shape (nstates,), optional, default=None
            The initial probability distribution, if samples are not to be taken from equilibrium.
        dtype : numpy.dtype, optional, default=numpy.int32
            The numpy dtype to use to store the synthetic trajectory.

        Returns
        -------
        states : np.array of shape (nstates,) of dtype=np.int32
            The trajectory of hidden states, with each element in range(0,nstates).

        Examples
        --------

        Generate a synthetic state trajectory of a specified length.

        >>> from bhmm import testsystems
        >>> model = testsystems.dalton_model()
        >>> states = model.generate_synthetic_state_trajectory(length=100)

        """
        states = np.zeros([length], dtype=dtype)

        # Generate first state sample.
        if initial_Pi is not None:
            states[0] = np.random.choice(range(self._nstates), size=1, p=initial_Pi)
        else:
            states[0] = np.random.choice(range(self._nstates), size=1, p=self._Pi)

        # Generate subsequent samples.
        for t in range(1,length):
            states[t] = np.random.choice(range(self._nstates), size=1, p=self._Tij[states[t-1],:])

        return states

    def generate_synthetic_observation(self, state):
        """Generate a synthetic observation from a given state.

        Parameters
        ----------
        state : int
            The index of the state from which the observable is to be sampled.

        Returns
        -------
        observation : float
            The observation from the given state.

        Examples
        --------

        Generate a synthetic observation from a single state.

        >>> from bhmm import testsystems
        >>> model = testsystems.dalton_model()
        >>> observation = model.generate_synthetic_observation(0)

        """
        return self.output_model.generate_observation_from_state(state)

    def generate_synthetic_observation_trajectory(self, length, initial_Pi=None, dtype=None):
        """Generate a synthetic realization of observables.

        Parameters
        ----------
        length : int
            Length of synthetic state trajectory to be generated.
        initial_Pi : np.array of shape (nstates,), optional, default=None
            The initial probability distribution, if samples are not to be taken from equilibrium.
        dtype : numpy.dtype, optional, default=None
            The numpy dtype to use to store the synthetic trajectory.  If None, will use default dtype.

        Returns
        -------
        o_t : np.array of shape (nstates,) of dtype=np.float32
            The trajectory of observations.
        s_t : np.array of shape (nstates,) of dtype=np.int32
            The trajectory of hidden states, with each element in range(0,nstates).

        Examples
        --------

        Generate a synthetic observation trajectory for an equilibrium realization.

        >>> from bhmm import testsystems
        >>> model = testsystems.dalton_model()
        >>> [o_t, s_t] = model.generate_synthetic_observation_trajectory(length=100)

        Use an initial nonequilibrium distribution.

        >>> from bhmm import testsystems
        >>> model = testsystems.dalton_model()
        >>> [o_t, s_t] = model.generate_synthetic_observation_trajectory(length=100, initial_Pi=np.array([1,0,0]))

        """
        # First, generate synthetic state trajetory.
        s_t = self.generate_synthetic_state_trajectory(length, initial_Pi=initial_Pi)

        # Next, generate observations from these states.
        o_t = self.output_model.generate_observation_trajectory(s_t, dtype=dtype)

        return [o_t, s_t]

    def generate_synthetic_observation_trajectories(self, ntrajectories, length, initial_Pi=None, dtype=None):
        """Generate a number of synthetic realization of observables from this model.

        Parameters
        ----------
        ntrajectories : int
            The number of trajectories to be generated.
        length : int
            Length of synthetic state trajectory to be generated.
        initial_Pi : np.array of shape (nstates,), optional, default=None
            The initial probability distribution, if samples are not to be taken from equilibrium.
        dtype : numpy.dtype, optional, default=None
            The numpy dtype to use to store the synthetic trajectory.  If None, will use default.

        Returns
        -------
        O : list of np.array of shape (nstates,) of dtype=np.float32
            The trajectories of observations
        S : list of np.array of shape (nstates,) of dtype=np.int32
            The trajectories of hidden states

        Examples
        --------

        Generate a number of synthetic trajectories.

        >>> from bhmm import testsystems
        >>> model = testsystems.dalton_model()
        >>> [O, S] = model.generate_synthetic_observation_trajectories(ntrajectories=10, length=100)

        Use an initial nonequilibrium distribution.

        >>> from bhmm import testsystems
        >>> model = testsystems.dalton_model(nstates=3)
        >>> [O, S] = model.generate_synthetic_observation_trajectories(ntrajectories=10, length=100, initial_Pi=np.array([1,0,0]))

        """
        O = list() # observations
        S = list() # state trajectories
        for trajectory_index in range(ntrajectories):
            [o_t, s_t] = self.generate_synthetic_observation_trajectory(length=length, initial_Pi=initial_Pi, dtype=dtype)
            O.append(o_t)
            S.append(s_t)

        return [O, S]

