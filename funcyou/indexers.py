def column(mtx):
    '''Returns an indexable that returns a column of the matrix when indexed.
    
    >>> a = ((1,2,3)
    ...      (4,5,6)
    ...      (7,8,9))
    >>> tuple(column(a)[0])
    (1,4,7) 
    '''
    class _column(object):
        def __getitem__(self, idx):
            return [i[idx] for i in mtx]
    return _column()

def diag(mtx):
    '''Returns an indexable that returns a diagonal of the matrix when indexed.
    '''
    class _diag(object):
        def __getitem__(self, idx):
            l = len(mtx)
            return [mtx[i][(i+idx)%l] for i in range(l)]
    return _diag()

def adiag(mtx):
    '''Returns an indexable that returns a antidiagonal of the matrix when indexed.
    '''
    class _adiag(object):
        def __getitem__(self, idx):
            l = len(mtx)
            return [mtx[i][(idx-i)%l] for i in range(l)]
    return _rdiag()


