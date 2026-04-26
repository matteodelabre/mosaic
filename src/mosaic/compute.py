from collections import defaultdict
from collections.abc import Mapping, Set

import numpy as np
import numpy.typing as npt
from pypoman import compute_polytope_vertices
from scipy.optimize import linprog


def find_extents(vectors: npt.ArrayLike) -> npt.ArrayLike:
    """
    Find minimum coordinate in each dimension of any point in vector-defined polytopes.

    :param vectors: set of vectors describing the polytopes
    :returns: minimum extents
    """
    dims = vectors.shape[1] - 1
    extents = np.zeros(dims)

    for i, vector in enumerate(vectors):
        # For each vector and its associated polytope, find, for each dimension,
        # the point inside the polytope with the lowest coordinate in that dimension
        vec_hspaces = vector - vectors
        vec_hspaces = np.delete(vec_hspaces, (i,), axis=0)

        for i in range(dims):
            objective = np.zeros(dims)
            objective[i] = 1
            sol = linprog(
                objective, A_ub=vec_hspaces[:, :-1], b_ub=-vec_hspaces[:, -1:]
            )

            if sol.x is None:
                break

            extents[i] = max(extents[i], sol.x[i])

    extents += np.ones(dims)
    return extents


def compute_polytope_center(
    hspaces_A: npt.ArrayLike,
    hspaces_b: npt.ArrayLike,
) -> npt.ArrayLike | None:
    """
    Compute the Chebyshev center of a polytope defined by Ax ⩽ b halfspaces.

    :param hspaces_A: `A` component of the halfspace inequation
    :param hspaces_b: `b` component of the halfspace inequation
    :returns: Chebyshev center, or None if infeasible
    """
    # (adapted from SciPy docs on HalfspaceIntersection)
    norm_vector = np.reshape(np.linalg.norm(hspaces_A, axis=1), (len(hspaces_A), 1))
    objective = np.zeros((hspaces_A.shape[1] + 1,))
    objective[-1] = -1
    hspaces_A = np.hstack((hspaces_A, norm_vector))
    res = linprog(objective, A_ub=hspaces_A, b_ub=hspaces_b)

    if res.x is None:
        return None

    center = res.x[:-1]
    return center


Point = tuple[float, ...]
Region = Set[Point]
Regions = Mapping[Region, Set[Point]]
Centers = Mapping[Region, Point]


def find_regions(
    vectors: npt.ArrayLike,
    slice_last: bool = True,
) -> tuple[Regions, Centers]:
    """
    Compute the region of optimality for each vector of a set of vectors.

    For each vector V, find the vertices of the convex polytope containing all points P
    of non-negative coordinates such that `V · Pᵀ ⩽ V' · Pᵀ` holds for all other
    vectors V' from :param:`vectors`.

    :param vectors: input vectors as rows of a matrix
    :param extents: maximum value on each dimension
    :param slice_last: if True (the default), the points are constrained so that their
        last coordinate equals 1, hence the returned solutions are one dimension less
        than the dimensions of :param:`vectors`. other solutions may be obtained by
        scaling all coordinates by a positive factor
    :return: pair of dictionary associating each polytope coordinates to the
        corresponding set of input vectors and to its center point
    """
    vectors = np.unique(vectors, axis=0)

    if not slice_last:
        vectors = np.hstack((vectors, np.zeros((vectors.shape[0], 1))))

    extents = find_extents(vectors)
    dims = vectors.shape[1]

    if dims - 1 != len(extents):
        raise ValueError("invalid extents dimension")

    # Constrain the polytopes to non-negative coordinates and to the given extent values
    nonneg_hspaces = -np.eye(dims)[:-1]
    extent_hspaces = np.hstack((np.eye(dims - 1), -np.array(extents)[:, np.newaxis]))

    regions = defaultdict(set)
    centers = {}

    for i, vector in enumerate(vectors):
        out_dims = dims if slice_last else dims - 1
        key = tuple(vector[:out_dims].tolist())

        vec_hspaces = np.delete(vector - vectors, (i,), axis=0)
        hspaces = np.vstack((vec_hspaces, nonneg_hspaces, extent_hspaces))
        hspaces_A = hspaces[:, :-1]
        hspaces_b = -hspaces[:, -1:]

        center = compute_polytope_center(hspaces_A, hspaces_b)
        vertices = compute_polytope_vertices(hspaces_A, hspaces_b)

        vertices_py = frozenset(
            tuple(round(float(coord), 14) for coord in vertex) for vertex in vertices
        )
        regions[vertices_py].add(key)
        centers[vertices_py] = center

    return regions, centers
