
from zope.interface import Interface, Attribute

__all__ = ["IKeyValueObserver", "IKeyValueObservable", "IRangeObserver", "IRangeObservable"]

class IKeyValueObserver(Interface):
    """Interface for classes which observe other object's properties."""
    
    def observedPropertyWillChange(srcobject, propertyName):
        """
        Callback if the property with the given name is about to change on the
        source object.
        """
    
    def observedPropertyDidChange(srcobject, propertyName):
        """
        Callback if the property with the given name has changed on the
        source object.
        """

class IKeyValueObservable(Interface):
    """Interface for classes which allow observation of their properties."""
    
    def addObserver(observer, propertyNames=None):
        """
        Add an observer to this object. The observer must implement the
        IKeyValueObserver interface. The object will hold a weak reference
        to the observer object.
        
        Optionally you may specify the propertyNames you want to observe, if no
        properties are specified, all properties will be observed.
        
        Calling this method more than once with the same observer object will
        add the specified properties to the existing list of observed
        properties.
        """
    
    def removeObserver(observer, propertyNames=None):
        """
        Removes an observer from this object.
        
        The observer actually gets removed if all of the properties it observes
        get removed. If no propertyNames are specified to this method, this is
        the default case.
        """

class IRangeObserver(Interface):
    """
    Interface for classes which observe range changes in subscriptable objects.
    
    `rangeFrom` allways denotes the first value that has been
    changed/added/removed (inclusive). `rangeTo` denotes the last changed value
    plus one (exclusive). `rangeTo` minus `rangeFrom` is always non-zero.
    """
    
    def observedRangeWillChange(srcobject, rangeFrom, rangeTo):
        """Callback if values in the source object are about to change."""
    
    def observedRangeDidChange(srcobject, rangeFrom, rangeTo):
        """Callback if values in the source object have changed."""
    
    def observedRangeWillIncrease(srcobject, rangeFrom, rangeTo):
        """Callback if new values are about to be added to the source object."""
    
    def observedRangeDidIncrease(srcobject, rangeFrom, rangeTo):
        """Callback if new values have been added to the source object."""
    
    def observedRangeWillDecrease(srcobject, rangeFrom, rangeTo):
        """Callback if values are about to be removed from the source object."""
    
    def observedRangeDidDecrease(srcobject, rangeFrom, rangeTo):
        """Callback if values have been removed from the source object."""

class IRangeObservable(Interface):
    """
    Interface for subscriptable classes which allow observation of their ranges.
    """
    
    def addRangeObserver(rangeObserver):
        """
        Add a range observer to this object. The observer must implement the
        IRangeObserver interface. The object will hold a weak reference
        to the observer object.
        """
    
    def removeRangeObserver(rangeObserver):
        """Removes a range observer from this object."""
