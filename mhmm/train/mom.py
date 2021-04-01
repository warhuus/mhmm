#%%

from typing import Union, List

import torch
import numpy as np
from numpy import ndarray
import scipy.linalg


def form_L(B312: List[np.ndarray], k: int) -> ndarray:
    ''' Return L, R3 '''
    L = np.empty((k, k))

    # step 1: compute R3 that diagonalizes B312[0]
    L[0], R3 = scipy.linalg.eig(B312[0])
    
    # step 2: obtain the diagonals of the matrices R3^-1 @ B312[j] @ R3
    # for all but the first entry.
    R3_inv = np.linalg.inv(R3)
    for i in range(1, k):
        L[i] = np.diag(R3_inv.dot(B312[i]).dot(R3))
    
    return L, R3


def sample_rotation_matrix(k: int) -> np.ndarray:
    ''' Make sample rotation matrix Theta '''
    theta, R = np.linalg.qr(np.random.normal(size=(k, k)))
    theta = theta @ np.diag(np.sign(np.diag(R)))

    if np.linalg.det(theta) < 0:
        theta[:, [0, 1]] = theta[:, [1, 0]]

    return theta


def make_P32(X, discrete: bool = False):
    ''' Compute P32 '''
    P32 = [np.einsum('i, j -> ij', X[i + 1], X[i])
           for i in range(1, len(X) - 1)]
        
    return sum(P32) / len(P32)


def make_P31(X, discrete: bool = False):
    ''' Compute P31 '''
    P31 = [np.einsum('i, j -> ij', X[i + 2], X[i])
           for i in range(0, len(X) - 2)]
    return sum(P31) / len(P31)


def make_P312(X, discrete: bool = False):
    ''' Compute P_312 '''
    P312 = [np.einsum('i, j, k -> ijk', X[i + 2], X[i], X[i + 1])
            for i in range(0, len(X) - 2)]
    return sum(P312) / len(P312)


def run(X, k: int) -> ndarray:
    '''
    Anandkumar, et al. 2012 algorithm B. Code inspired by maxentile:
    https://github.com/maxentile/method-of-moments-tinker/blob/master/HMM%20method%20of%20moments.ipynb

    Inputs:
        X: N x D... I think we need to subtract the mean.
        
    '''

    # make P matrices
    P31 = make_P31(X)
    P32 = make_P32(X)
    P312 = make_P312(X)

    # compute top-k singular vectors
    U3, _, U1 = np.linalg.svd(P31)
    _, _, U2 = np.linalg.svd(P32)

    U1 = U1[:, :k]
    U2 = U2[:, :k]
    U3 = U3[:, :k]

    # pick invertible theta
    theta = sample_rotation_matrix(k)

    # form B312(U2 theta_j) for all j
    P312_U3_theta = [P312.dot(U2.dot(theta[j])) for j in range(k)]
    B312 = [
        (U3.T.dot(P312_U3_theta[j]).dot(U1)).dot(
        np.linalg.inv(U3.T.dot(P31).dot(U1)))
        for j in range(k)
    ]

    # form matrix L
    L, R3 = form_L(B312, k)

    # form and return M2
    M2 = U2.dot(np.linalg.inv(theta).dot(L))
    emission_probs = np.real(M2)

    # get transition matrix
    transmat = np.real(np.linalg.inv(U3.T.dot(emission_probs)).dot(R3))
    transmat = transmat / transmat.sum(axis=0).T

    return emission_probs, transmat
