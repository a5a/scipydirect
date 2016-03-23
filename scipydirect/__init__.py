# -*- coding: utf-8 -*-
"""
scipydirect - A python wrapper to the DIRECT algorithm.
=======================================================

DIRECT is a method to solve global bound constraint optimization problems and
was originally developed by D. R. Jones, C. D. Perttunen and B. E. Stuckmann.
It is designed to find **global** solutions of mathematical optimization problems of the from

.. math::

       \min_ {x \in R^n} f(x)

subject to

.. math::

       x_L \leq  x  \leq x_U

Where :math:`x` are the optimization variables (with upper an lower
bounds), :math:`f(x)` is the objective function.

The DIRECT package uses the fortan implementation of DIRECT written by
Joerg.M.Gablonsky, DIRECT Version 2.0.4. More information on the DIRECT
algorithm can be found in Gablonsky's `thesis <http://repository.lib.ncsu.edu/ir/bitstream/1840.16/3920/1/etd.pdf>`_.

.. codeauthor:: Andreas Mayer <andisspam@gmail.com>, Amit Aides <amitibo@tx.technion.ac.il>
"""

import numpy as np
from .direct import direct


__version_info__ = ('1', '0')
__version__ = '.'.join(__version_info__)

ERROR_MESSAGES = (
    'Maximum number of levels has been reached.',
    'An error occured while the function was sampled',
    'There was an error in the creation of the sample points',
    'Initialization failed',
    'maxf is too large'
    'u[i] < l[i] for some i'
)

SUCCESS_MESSAGES = (
    'Number of function evaluations done is larger then maxf',
    'Number of iterations is equal to maxT',
    'The best function value found is within fglper of the (known) global optimum',
    'The volume of the hyperrectangle with best function value found is below volper',
    'The volume of the hyperrectangle with best function value found is smaller then volper'
)

# Class for returning the result of an optimization algorithm (copied from
# scipy.optimize)
class OptimizeResult(dict):
    """ Represents the optimization result.

    Attributes
    ----------
    x : ndarray
        The solution of the optimization.
    success : bool
        Whether or not the optimizer exited successfully.
    status : int
        Termination status of the optimizer. Its value depends on the
        underlying solver. Refer to `message` for details.
    message : str
        Description of the cause of the termination.
    fun, jac, hess, hess_inv : ndarray
        Values of objective function, Jacobian, Hessian or its inverse (if
        available). The Hessians may be approximations, see the documentation
        of the function in question.
    nfev, njev, nhev : int
        Number of evaluations of the objective functions and of its
        Jacobian and Hessian.
    nit : int
        Number of iterations performed by the optimizer.
    maxcv : float
        The maximum constraint violation.

    Notes
    -----
    There may be additional attributes not listed above depending of the
    specific solver. Since this class is essentially a subclass of dict
    with attribute accessors, one can see which attributes are available
    using the `keys()` method.
    """
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __repr__(self):
        if self.keys():
            m = max(map(len, list(self.keys()))) + 1
            return '\n'.join([k.rjust(m) + ': ' + repr(v)
                              for k, v in self.items()])
        else:
            return self.__class__.__name__ + "()"

def minimize(func, bounds=None, nvar=None, args=(), disp=False,
             eps=1e-4,
             maxf=20000,
             maxT=6000,
             algmethod=0,
             fglobal=-1e100,
             fglper=0.01,
             volper=-1.0,
             sigmaper=-1.0,
             logfilename='DIRresults.txt',
             ):
    """
    Solve an optimization problem using the DIRECT (Dividing Rectangles) algorithm.
    It can be used to solve general nonlinear programming problems of the form:

    .. math::

           \min_ {x \in R^n} f(x)

    subject to

    .. math::

           x_L \leq  x  \leq x_U
    
    Where :math:`x` are the optimization variables (with upper an lower
    bounds), :math:`f(x)` is the objective function.

    Parameters
    ----------
    func : function pointer
        Callback function for evaluating objective function.
        The callback functions accepts two parameters: x (value of the
        optimization variables at which the objective is to be evaluated) and
        user_data, an arbitrary data object supplied by the user.
        The function should return a tuple of two values: the objective function
        value at the point x and a value (flag) that is set to 1 if the function
        is not defined at point x (0 if it is defined).
    
    bounds : array-like
            ``(min, max)`` pairs for each element in ``x``, defining
            the bounds on that parameter.
        
    eps : float
        Ensures sufficient decrease in function value when a new potentially
        optimal interval is chosen.

    maxf : integer
        Approximate upper bound on objective function evaluations.
        
        .. note::
        
            Maximal allowed value is 90000 see documentation of fortran library.
    
    maxT : integer
        Maximum number of iterations.
        
        .. note::
        
            Maximal allowed value is 6000 see documentation of fortran library.
        
    algmethod : integer
        Whether to use the original or modified DIRECT algorithm. Possible values:
        
        * ``algmethod=0`` - use the original DIRECT algorithm
        * ``algmethod=1`` - use the modified DIRECT-l algorithm
    
    fglobal : float
        Function value of the global optimum. If this value is not known set this
        to a very large negative value.
        
    fglper : float
        Terminate the optimization when the percent error satisfies:
        
        .. math::

            100*(f_{min} - f_{global})/\max(1, |f_{global}|) \leq f_{glper}
        
    volper : float
        Terminate the optimization once the volume of a hyperrectangle is less
        than volper percent of the original hyperrectangel.
        
    sigmaper : float
        Terminate the optimization once the measure of the hyperrectangle is less
        than sigmaper.
        
    logfilename : string
        Name of logfile.
    
    Returns
    -------
    res : OptimizeResult
        The optimization result represented as a ``OptimizeResult`` object.
        Important attributes are: ``x`` the solution array, ``success`` a
        Boolean flag indicating if the optimizer exited successfully and
        ``message`` which describes the cause of the termination. See
        `OptimizeResult` for a description of other attributes.

    """
    
    if bounds is None:
        l = np.zeros(nvar, dtype=np.float64)
        u = np.ones(nvar, dtype=np.float64)
    else:
        bounds = np.asarray(bounds)
        l = bounds[:, 0] 
        u = bounds[:, 1] 

    def _objective_wrap(x, iidata, ddata, cdata, n, iisize, idsize, icsize):
        """
        To simplify the python objective we use a wrapper objective that complies
        with the required fortran objective.
        """
        return func(x, *args), 0

    #
    # Dummy values so that the python wrapper will comply with the required
    # signature of the fortran library.
    #
    iidata = np.ones(0, dtype=np.int32)
    ddata = np.ones(0, dtype=np.float64)
    cdata = np.ones([0,40], dtype=np.uint8)

    #
    # Call the DIRECT algorithm
    #
    x, fun, ierror = direct(
                        _objective_wrap,
                        eps,
                        maxf,
                        maxT,
                        l,
                        u,
                        algmethod,
                        logfilename, 
                        fglobal,
                        fglper,
                        volper,
                        sigmaper,
                        iidata,
                        ddata,
                        cdata
                        )

    if ierror < 0:
        print ierror
        raise Exception(ERROR_MESSAGES[abs(ierror)-1])
        
    return OptimizeResult(x=x,fun=fun, status=ierror)