__author__ = 'noe'

import numpy as np
from bhmm.hmm_class import HMM
from bhmm.output_models.discrete import DiscreteOutputModel

import warnings

def initial_model_discrete(observations, nstates, lag=1, reversible=True, verbose=False):
    """Generate an initial model with discrete output densities

    Parameters
    ----------
    observations : list of ndarray((T_i), dtype=int)
        list of arrays of length T_i with observation data
    nstates : int
        The number of states.
    lag : int, optional, default=1
        The lag time to use for initializing the model.
    verbose : bool, optional, default=False
        If True, will be verbose in output.

    TODO
    ----
    * Why do we have a `lag` option?  Isn't the HMM model, by definition, lag=1 everywhere?  Why would this be useful instead of just having the user subsample the data?

    Examples
    --------

    Generate initial model for a discrete output model.

    >>> from bhmm import testsystems
    >>> [model, observations, states] = testsystems.generate_synthetic_observations(output_model_type='discrete')
    >>> initial_model = initial_model_discrete(observations, model.nstates)

    """
    # check input
    if not reversible:
        warnings.warn("nonreversible initialization of discrete HMM currently not supported. Using a reversible matrix for initialization.")
        reversible = True

    # import emma inside function in order to avoid dependency loops
    from pyemma import msm

    # estimate Markov model
    MSM = msm.estimate_markov_model(observations, lag, reversible=True, connectivity='largest')

    # PCCA
    pcca = MSM.pcca(nstates)

    # HMM output matrix
    B_conn = MSM.metastable_distributions

    #print 'B_conn = \n',B_conn
    # full state space output matrix
    eps = 0.01 * (1.0/MSM.nstates) # default output probability, in order to avoid zero columns
    B = eps * np.ones((nstates,MSM.nstates), dtype=np.float64)
    # expand B_conn to full state space
    B[:,MSM.active_set] = B_conn[:,:]
    # renormalize B to make it row-stochastic
    B /= B.sum(axis=1)[:,None]

    # coarse-grained transition matrix
    M = pcca.memberships
    W = np.linalg.inv(np.dot(M.T, M))
    A = np.dot(np.dot(M.T, MSM.transition_matrix), M)
    P_coarse = np.dot(W, A)

    # symmetrize and renormalize to eliminate numerical errors
    X = np.dot(np.diag(pcca.coarse_grained_stationary_probability), P_coarse)
    # if there are values < 0, set to eps
    X = np.maximum(X, eps)
    # turn into coarse-grained transition matrix
    A = X / X.sum(axis=1)[:, None]

    if verbose:
        print 'Initial model: '
        print 'A = \n',A
        print 'B.T = \n'
        for i in range(B.shape[1]):
            print B[0,i],B[1,i]
        print

    # initialize HMM
    # --------------
    output_model = DiscreteOutputModel(B)
    model = HMM(nstates, A, output_model)
    return model


