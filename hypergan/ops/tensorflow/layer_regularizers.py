class layer_norm_1(object):
    def __init__(self, batch_size,  epsilon=1e-5, momentum = 0.1, name="layer_norm"):
        self.name = name
    def __call__(self, x, train=True):
        return tf.contrib.layers.layer_norm(x, scope=self.name, center=True, scale=True)


class batch_norm_1(object):
    """Code modification of http://stackoverflow.com/a/33950177

    """
    def __init__(self, batch_size, epsilon=1e-5, momentum = 0.1, name="batch_norm", half=None):
        assert half is None
        del momentum # unused
        with tf.variable_scope(name) as scope:
            self.epsilon = epsilon
            self.batch_size = batch_size

            self.name=name

    def __call__(self, x, train=True):
        del train # unused

        shape = x.get_shape().as_list()

        needs_reshape = len(shape) != 4
        if needs_reshape:
            orig_shape = shape
            if len(shape) == 2:
                x = tf.reshape(x, [shape[0], 1, 1, shape[1]])
            elif len(shape) == 1:
                x = tf.reshape(x, [shape[0], 1, 1, 1])
            else:
                assert False, shape
            shape = x.get_shape().as_list()

        with tf.variable_scope(self.name) as scope:
            self.gamma = tf.get_variable("gamma", [shape[-1]],dtype=config['dtype'],
                                initializer=tf.random_normal_initializer(1., 0.02,dtype=config['dtype']))
            self.beta = tf.get_variable("beta", [shape[-1]],dtype=config['dtype'],
                                initializer=tf.constant_initializer(0.,dtype=config['dtype']))

            self.mean, self.variance = tf.nn.moments(x, [0, 1, 2])

            out =  tf.nn.batch_norm_with_global_normalization(
                x, self.mean, self.variance, self.beta, self.gamma, self.epsilon,
                scale_after_normalization=True)
            if needs_reshape:
                out = tf.reshape(out, orig_shape)
            return out

TRAIN_MODE = True
class conv_batch_norm(object):
    """Code modification of http://stackoverflow.com/a/33950177"""
    def __init__(self, name="batch_norm", epsilon=1e-5, momentum=0.1,
        in_dim=None):
        with tf.variable_scope(name) as scope:
            self.epsilon = epsilon
            self.momentum = momentum
            self.name = name
            self.in_dim = in_dim
            global TRAIN_MODE
            self.train = TRAIN_MODE
            self.ema = tf.train.ExponentialMovingAverage(decay=0.9)
            print("initing %s in train: %s" % (scope.name, self.train))

    def __call__(self, x):
        shape = x.get_shape()
        shp = self.in_dim or shape[-1]
        with tf.variable_scope(self.name) as scope:
            self.gamma = tf.get_variable("gamma", [shp],dtype=config['dtype'],
                                         initializer=tf.random_normal_initializer(1., 0.02,dtype=config['dtype']))
            self.beta = tf.get_variable("beta", [shp],dtype=config['dtype'],
                                        initializer=tf.constant_initializer(0.,dtype=config['dtype']))

            self.mean, self.variance = tf.nn.moments(x, [0, 1, 2])
            self.mean.set_shape((shp,))
            self.variance.set_shape((shp,))
            self.ema_apply_op = self.ema.apply([self.mean, self.variance])

            if self.train:
                # with tf.control_dependencies([self.ema_apply_op]):
                normalized_x = tf.nn.batch_norm_with_global_normalization(
                        x, self.mean, self.variance, self.beta, self.gamma, self.epsilon,
                        scale_after_normalization=True)
            else:
                normalized_x = tf.nn.batch_norm_with_global_normalization(
                    x, self.ema.average(self.mean), self.ema.average(self.variance), self.beta,
                    self.gamma, self.epsilon,
                    scale_after_normalization=True)
            return normalized_x

class fc_batch_norm(conv_batch_norm):
    def __call__(self, fc_x):
        ori_shape = fc_x.get_shape().as_list()
        if ori_shape[0] is None:
            ori_shape[0] = -1
        new_shape = [ori_shape[0], 1, 1, ori_shape[1]]
        x = tf.reshape(fc_x, new_shape)
        normalized_x = super(fc_batch_norm, self).__call__(x)
        return tf.reshape(normalized_x, ori_shape)


class batch_norm_second_half(object):
    """Code modification of http://stackoverflow.com/a/33950177

    """
    def __init__(self, epsilon=1e-5,  name="batch_norm"):
        with tf.variable_scope(name) as scope:
            self.epsilon = epsilon

            self.name=name

    def __call__(self, x):

        shape = x.get_shape().as_list()

        needs_reshape = len(shape) != 4
        if needs_reshape:
            orig_shape = shape
            if len(shape) == 2:
                x = tf.reshape(x, [shape[0], 1, 1, shape[1]])
            elif len(shape) == 1:
                x = tf.reshape(x, [shape[0], 1, 1, 1])
            else:
                assert False, shape
            shape = x.get_shape().as_list()

        with tf.variable_scope(self.name) as scope:
            self.gamma = tf.get_variable("gamma", [shape[-1]],dtype=config['dtype'],
                                initializer=tf.random_normal_initializer(1., 0.02,dtype=config['dtype']))
            self.beta = tf.get_variable("beta", [shape[-1]],dtype=config['dtype'],
                                initializer=tf.constant_initializer(0.,dtype=config['dtype']))

            second_half = tf.slice(x, [shape[0] // 2, 0, 0, 0],
                                      [shape[0] // 2, shape[1], shape[2], shape[3]])

            self.mean, self.variance = tf.nn.moments(second_half, [0, 1, 2])

            out =  tf.nn.batch_norm_with_global_normalization(
                x, self.mean, self.variance, self.beta, self.gamma, self.epsilon,
                scale_after_normalization=True)
            if needs_reshape:
                out = tf.reshape(out, orig_shape)
            return out

class batch_norm_first_half(object):
    """Code modification of http://stackoverflow.com/a/33950177

    """
    def __init__(self, epsilon=1e-5,  name="batch_norm"):
        with tf.variable_scope(name) as scope:
            self.epsilon = epsilon

            self.name=name

    def __call__(self, x):

        shape = x.get_shape().as_list()

        needs_reshape = len(shape) != 4
        if needs_reshape:
            orig_shape = shape
            if len(shape) == 2:
                x = tf.reshape(x, [shape[0], 1, 1, shape[1]])
            elif len(shape) == 1:
                x = tf.reshape(x, [shape[0], 1, 1, 1])
            else:
                assert False, shape
            shape = x.get_shape().as_list()

        with tf.variable_scope(self.name) as scope:
            self.gamma = tf.get_variable("gamma", [shape[-1]],dtype=config['dtype'],
                                initializer=tf.random_normal_initializer(1., 0.02,dtype=config['dtype']))
            self.beta = tf.get_variable("beta", [shape[-1]],dtype=config['dtype'],
                                initializer=tf.constant_initializer(0.,dtype=config['dtype']))

            first_half = tf.slice(x, [0, 0, 0, 0],
                                      [shape[0] // 2, shape[1], shape[2], shape[3]])

            self.mean, self.variance = tf.nn.moments(first_half, [0, 1, 2])

            out =  tf.nn.batch_norm_with_global_normalization(
                x, self.mean, self.variance, self.beta, self.gamma, self.epsilon,
                scale_after_normalization=True)
            if needs_reshape:
                out = tf.reshape(out, orig_shape)
            return out

def avg_grads(tower_grads):
  """Calculate the average gradient for each shared variable across all towers.

  Note that this function provides a synchronization point across all towers.

  Args:
    tower_grads: List of lists of (gradient, variable) tuples. The outer list
      is over individual gradients. The inner list is over the gradient
      calculation for each tower.
  Returns:
     List of pairs of (gradient, variable) where the gradient has been averaged
     across all towers.
  """
  average_grads = []
  for grad_and_vars in zip(*tower_grads):
    # Note that each grad_and_vars looks like the following:
    #   ((grad0_gpu0, var0_gpu0), ... , (grad0_gpuN, var0_gpuN))
    grads = []
    for g, _ in grad_and_vars:
      # Add 0 dimension to the gradients to represent the tower.
      expanded_g = tf.expand_dims(g, 0)

      # Append on a 'tower' dimension which we will average over below.
      grads.append(expanded_g)

    # Average over the 'tower' dimension.
    grad = tf.concat(axis=0, values=grads)
    grad = tf.reduce_mean(grad, 0)

    # Keep in mind that the Variables are redundant because they are shared
    # across towers. So .. we will just return the first tower's pointer to
    # the Variable.
    v = grad_and_vars[0][1]
    grad_and_var = (grad, v)
    average_grads.append(grad_and_var)
  return average_grads

class batch_norm_cross(object):
    def __init__(self, epsilon=1e-5,  name="batch_norm", dtype=tf.float32):
        with tf.variable_scope(name) as scope:
            self.epsilon = epsilon
            self.name=name

    def __call__(self, x):

        shape = x.get_shape().as_list()

        needs_reshape = len(shape) != 4
        if needs_reshape:
            orig_shape = shape
            if len(shape) == 2:
                x = tf.reshape(x, [shape[0], 1, 1, shape[1]])
            elif len(shape) == 1:
                x = tf.reshape(x, [shape[0], 1, 1, 1])
            else:
                assert False, shape
            shape = x.get_shape().as_list()

        with tf.variable_scope(self.name) as scope:
            self.gamma0 = tf.get_variable("gamma0", [shape[-1] // 2],dtype=config.dtype,
                                initializer=tf.random_normal_initializer(1., 0.02, dtype=config.dtype))
            self.beta0 = tf.get_variable("beta0", [shape[-1] // 2],
                                initializer=tf.constant_initializer(0., dtype=config.dtype))
            self.gamma1 = tf.get_variable("gamma1", [shape[-1] // 2],dtype=config.dtype,
                                initializer=tf.random_normal_initializer(1., 0.02,dtype=config.dtype))
            self.beta1 = tf.get_variable("beta1", [shape[-1] // 2],dtype=config.dtype,
                                initializer=tf.constant_initializer(0.,dtype=config.dtype))

            ch0 = tf.slice(x, [0, 0, 0, 0],
                              [shape[0], shape[1], shape[2], shape[3] // 2])
            ch1 = tf.slice(x, [0, 0, 0, shape[3] // 2],
                              [shape[0], shape[1], shape[2], shape[3] // 2])

            ch0b0 = tf.slice(ch0, [0, 0, 0, 0],
                                  [shape[0] // 2, shape[1], shape[2], shape[3] // 2])

            ch1b1 = tf.slice(ch1, [shape[0] // 2, 0, 0, 0],
                                  [shape[0] // 2, shape[1], shape[2], shape[3] // 2])


            ch0_mean, ch0_variance = tf.nn.moments(ch0b0, [0, 1, 2])
            ch1_mean, ch1_variance = tf.nn.moments(ch1b1, [0, 1, 2])

            ch0 =  tf.nn.batch_norm_with_global_normalization(
                ch0, ch0_mean, ch0_variance, self.beta0, self.gamma0, self.epsilon,
                scale_after_normalization=True)

            ch1 =  tf.nn.batch_norm_with_global_normalization(
                ch1, ch1_mean, ch1_variance, self.beta1, self.gamma1, self.epsilon,
                scale_after_normalization=True)

            out = tf.concat(axis=3, values=[ch0, ch1])

            if needs_reshape:
                out = tf.reshape(out, orig_shape)

            return out


