
from interface import *
from zope.interface import implements
from weakref import WeakKeyDictionary

try:
    # location in Python 2.7 and 3.1
    from weakref import WeakSet
except ImportError:
    # separately installed
    from weakrefset import WeakSet

__all__ = ["KVOBroker", "KVOProperty", "ROBroker"]

class KVOBroker(object):
    """
    Helper class which simplifies handling of key-value observers.
    
    Can be used as a mixin or standalone.
    """
    
    implements(IKeyValueObservable)
    
    __kvobservers = None
    
    def addObserver(self, observer, propertyNames=None):
        assert IKeyValueObserver.providedBy(observer)
        
        if self.__kvobservers == None:
            self.__kvobservers = WeakKeyDictionary()
        
        if propertyNames == None:
            self.__kvobservers[observer] = None
            return
        
        if isinstance(propertyNames, basestring):
            propertyNames = [propertyNames]
        
        propertyNames = set(propertyNames)
        
        if self.__kvobservers.has_key(observer):
            self.__kvobservers[observer] |= propertyNames
        else:
            self.__kvobservers[observer] = propertyNames
    
    def removeObserver(self, observer, propertyNames=None):
        assert IKeyValueObserver.providedBy(observer)
        
        if self.__kvobservers == None:
            return
        
        if self.__kvobservers.has_key(observer):
            if propertyNames == None:
                del self.__kvobservers[observer]
            else:
                self.__kvobservers[observer] -= propertyNames
                if len(self.__kvobservers[observer]) == 0:
                    del self.__kvobservers[observer]
    
    def notifyPropertyWillChange(self, propertyName, srcobject=None):
        """
        Call this to inform the respective observers of an impending change.
        
        You must call `notifyPropertyDidChange()` after you performed the
        changes. The call is not stackable.
        """
        
        if srcobject == None:
            srcobject = self
        self.__propertyName = propertyName
        self.__srcobject = srcobject
        
        if self.__kvobservers != None:
            for observer, propertyNames in dict(self.__kvobservers).iteritems():
                if propertyNames == None or propertyName in propertyNames:
                    observer.observedPropertyWillChange(srcobject, propertyName)
    
    def notifyPropertyDidChange(self):
        """
        Call this to inform the respective observers of a performed change.
        
        You must have called `notifyPropertyWillChange()` before.
        """
        
        if self.__kvobservers != None:
            for observer, propertyNames in dict(self.__kvobservers).iteritems():
                if propertyNames == None or self.__propertyName in propertyNames:
                    observer.observedPropertyDidChange(self.__srcobject, self.__propertyName)
        
        del self.__propertyName
        del self.__srcobject

class KVOProperty(object):
    """
    KVO-enabled property for classes which inherit from KVOBroker.
    """
    
    def __init__(self, name, default=None):
        self.__name = name
        self.__default = default
        self.__instanceValue = WeakKeyDictionary()
    
    def __get__(self, instance, owner):
        if instance == None:
            return self
        return self.__instanceValue.get(instance, self.__default)
    
    def __set__(self, instance, value):
        prev = self.__instanceValue.get(instance, self.__default)
        if value != prev:
            instance.notifyPropertyWillChange(instance, self.__name)
            self.__instanceValue[instance] = value
            instance.notifyPropertyDidChange()

class ROBroker(object):
    """
    Helper class which simplifies handling of range observers.
    
    Can be used as a mixin or standalone.
    """
    
    implements(IRangeObservable)
    
    __robservers = None
    
    def addRangeObserver(self, rangeObserver):
        assert IRangeObserver.providedBy(rangeObserver)
        
        if self.__robservers == None:
            self.__robservers = WeakSet()
        
        self.__robservers.add(rangeObserver)
    
    def removeRangeObserver(self, rangeObserver):
        assert IRangeObserver.providedBy(rangeObserver)
        
        if self.__robservers == None:
            return
        
        self.__robservers.discard(rangeObserver)
    
    def notifyRangeWillChange(self, rangeFrom, rangeTo, srcobject=None):
        """
        Call this to inform the respective observers of an impending range
        change.
        
        You must call `notifyRangeDidChange()` after you performed the
        range change. The call is not stackable.
        """
        
        if srcobject == None:
            srcobject = self
        self.__rangeFrom = rangeFrom
        self.__rangeTo = rangeTo
        self.__srcobject = srcobject
        
        if self.__robservers != None:
            for rangeObserver in set(self.__robservers):
                rangeObserver.observedRangeWillChange(srcobject, rangeFrom, rangeTo)
    
    def notifyRangeDidChange(self):
        """
        Call this to inform the respective observers of a performed range
        change.
        
        You must have called `notifyRangeWillChange()` before.
        """
        
        if self.__robservers != None:
            for rangeObserver in set(self.__robservers):
                rangeObserver.observedRangeDidChange(self.__srcobject, self.__rangeFrom, self.__rangeTo)
        
        del self.__rangeFrom
        del self.__rangeTo
        del self.__srcobject
    
    def notifyRangeWillIncrease(self, rangeFrom, rangeTo, srcobject=None):
        """
        Call this to inform the respective observers of an impending range
        increase.
        
        You must call `notifyRangeDidIncrease()` after you performed the
        range increase. The call is not stackable.
        """
        
        if srcobject == None:
            srcobject = self
        self.__rangeFrom = rangeFrom
        self.__rangeTo = rangeTo
        self.__srcobject = srcobject
        
        if self.__robservers != None:
            for rangeObserver in set(self.__robservers):
                rangeObserver.observedRangeWillIncrease(srcobject, rangeFrom, rangeTo)
    
    def notifyRangeDidIncrease(self):
        """
        Call this to inform the respective observers of a performed range
        increase.
        
        You must have called `notifyRangeWillIncrease()` before.
        """
        
        if self.__robservers != None:
            for rangeObserver in set(self.__robservers):
                rangeObserver.observedRangeDidIncrease(self.__srcobject, self.__rangeFrom, self.__rangeTo)
        
        del self.__rangeFrom
        del self.__rangeTo
        del self.__srcobject
    
    def notifyRangeWillDecrease(self, rangeFrom, rangeTo, srcobject=None):
        """
        Call this to inform the respective observers of an impending range
        decrease.
        
        You must call `notifyRangeDidDecrease()` after you performed the
        range decrease. The call is not stackable.
        """
        
        if srcobject == None:
            srcobject = self
        self.__rangeFrom = rangeFrom
        self.__rangeTo = rangeTo
        self.__srcobject = srcobject
        
        if self.__robservers != None:
            for rangeObserver in set(self.__robservers):
                rangeObserver.observedRangeWillDecrease(srcobject, rangeFrom, rangeTo)
    
    def notifyRangeDidDecrease(self):
        """
        Call this to inform the respective observers of a performed range
        decrease.
        
        You must have called `notifyRangeWillDecrease()` before.
        """
        
        if self.__robservers != None:
            for rangeObserver in set(self.__robservers):
                rangeObserver.observedRangeDidDecrease(self.__srcobject, self.__rangeFrom, self.__rangeTo)
        
        del self.__rangeFrom
        del self.__rangeTo
        del self.__srcobject
