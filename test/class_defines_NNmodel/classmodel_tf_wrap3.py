"""
class wrap the tensorflow model into a class
this simple neuron network, inspired by the demo code from https://danijar.com/structuring-your-tensorflow-models/
The self._atrrs are wrapped

@property
def func():
    ##do some thing###
    return self.func_a

is equivalent to

def func():
    ##do some thing###
func = property(func)  #wrap func by property()

In Python, property() is a built-in function that creates and returns a property object.
above code is also equivalent to

# make empty property
func = property()
# assign fget
func = func.getter(func) # this func.getter get the return object of func(), which self.func_a

usage:
python test.py

"""
import dill
import pickle
import cPickle
import traceback
import numpy as np
import functools
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data


# define model wrap for tensorflow lib
def tf_property( function ):
    """
    A decorator for functions that define TensorFlow operations. The wrapped
    function will only be executed once. Subsequent calls to it will directly
    return the result so that operations are added to the graph only once.
    """
    attribute = '_cache_' + function.__name__

    @property
    @functools.wraps(function)
    def decorator( self ):
        if not hasattr(self, attribute):
            #with tf.variable_scope(function.__name):
                #setattr(self, attribute, function(self))
            setattr(self, attribute, function(self))
        return getattr(self, attribute)
    return decorator

#wrapped model using tensorflow lib
#model contain data, target and model_abstract
class tf_model_wrap:
    def __init__( self, data, target, prediction_func, optimize_func, error_func ):
        self.data             = data
        self.target           = target
        self.arg              = None
        self._prediction_func = prediction_func
        self._optimize_func   = optimize_func
        self._error_func      = error_func
        self.prediction
        self.optimize
        self.error

    @tf_property
    def prediction( self ):
        return self._prediction_func(self)

    @tf_property
    def optimize( self ):
        return self._optimize_func(self)

    @tf_property
    def error( self ):
        return self._error_func(self)

#define the top level model that contains training and testing functions using tensorflow lib
class tf_model_top:
    # intialize tensorflow model
    def __init__( self, data_shape, target_shape, tf_prediction_func, tf_optimize_func, tf_error_func ):
        # tensorflow style data and target defination, as inputs to model
        self.data       = tf.placeholder(tf.float32, data_shape) # e.g. [None, 784]
        self.target     = tf.placeholder(tf.float32, target_shape) # e.g. [None, 10]
         # model first defined in abstract form, which contains prediction, optimize, error functions
        # put data, target and model together
        self.model_wrap = tf_model_wrap(self.data, self.target, tf_prediction_func, tf_optimize_func, tf_error_func)
        self.sess       = tf.Session()
        self.sess.run(tf.global_variables_initializer())

    # train neural network, using all training data, do mini-batch in this function
    def train_all_batch( self, train_data, train_target, N_example, N_batch, mini_batch_func ):
        #mini-batch
        batch_x, batch_y = mini_batch_func(N_example, N_batch, train_data, train_target)
        for _ in range(N_example//N_batch):
            self.sess.run(self.model_wrap.optimize, {self.data: batch_x, self.target: batch_y})            
        return self

    # simple training function, do one step training, should be putted in a loop for mini-batch
    def train( self, train_data, train_target ):
        self.sess.run(self.model_wrap.optimize, {self.data: train_data, self.target: train_target})
        return self

    # simple training function, do one step training, should be putted in a loop for mini-batch
    def prediction( self, data, target ):
        target = self.sess.run(self.model_wrap.prediction, {self.data: data, self.target: target})
        return target

    # test neural network using testing data
    def test( self, test_data, test_target ):
        error = self.sess.run(self.model_wrap.error, {self.data: test_data, self.target: test_target})
        print('Test error {:6.2f}%'.format(100 * error))
        return self

    # save the tensorflow model
    def save( self, name ):
        saver = tf.train.Saver(tf.global_variables())
        saver.save(self.sess, name)
        print('model saved')
        return self

    # restore the tensorflow model
    def restore( self, name ):
        nsaver = tf.train.Saver(tf.global_variables())
        nsaver.restore(self.sess, './'+name)
        print('model restored')
        return self

# these functions should be defined specifically for individal neural network
# example of the prediction function, defined using tensorflow lib
def tf_prediction_func( model ):
    #if model.arg is None:
    #    model.arg = [1.0, 1.0]
    # get data size
    data_size   = int(model.data.get_shape()[1])
    target_size = int(model.target.get_shape()[1])
    # one full connection layer
    weight      = tf.Variable(tf.truncated_normal([data_size, target_size]))
    bias        = tf.Variable(tf.constant(0.1, shape=[target_size]))
    # y = data * W + b
    y    = tf.nn.sigmoid(tf.matmul(model.data, weight) + bias)
    # softmax output
    return tf.nn.softmax(y)

# example of the prediction function, defined using tensorflow lib
def tf_optimize_func( model ):
    #model.arg = [0.5, 0.5]
    # cost funcion as cross entropy = y * log(y)
    cross_entropy = tf.reduce_mean(-tf.reduce_sum(model.target * tf.log(model.prediction), reduction_indices=[1]))
    #cross_entropy = -tf.reduce_sum(self.target * tf.log(self.prediction))
    optimizer = tf.train.RMSPropOptimizer(0.03)
    # minimization apply to cross_entropy
    return optimizer.minimize(cross_entropy)

# example of the error function, defined using tensorflow lib
def tf_error_func( model ):
    #model.arg = [1.0, 1.0]
    # mistakes as the difference between target and prediction, argmax as output layer
    mistakes = tf.not_equal(tf.argmax(model.target, 1), tf.argmax(model.prediction, 1))
    # error=cost(mistakes) = ||mistakes||_2
    return tf.reduce_mean(tf.cast(mistakes, tf.float32))

def test1():
    mnist = input_data.read_data_sets('./MNIST_data/', one_hot=True)
    model = tf_model_top([None, 784], [None, 10], tf_prediction_func, tf_optimize_func, tf_error_func)
    for _ in range(100):
        model.test(mnist.test.images, mnist.test.labels)
        for _ in range(100):
            batch_xs, batch_ys = mnist.train.next_batch(1000)            
            model.train(batch_xs, batch_ys)
    model.save('test_model_save')

def test2():
    mnist = input_data.read_data_sets('./MNIST_data/', one_hot=True)
    model = tf_model_top([None, 784], [None, 10], tf_prediction_func, tf_optimize_func, tf_error_func)
    model.restore('test_model_save')
    model.test(mnist.test.images, mnist.test.labels)
#if __name__ == '__main__':
    #test1()
