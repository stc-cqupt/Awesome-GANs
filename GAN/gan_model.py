import tensorflow as tf


tf.set_random_seed(777)  # reproducibility


class GAN:

    def __init__(self, s, batch_size=32, input_height=28, input_width=28, channel=1, n_classes=10,
                 sample_num=64, sample_size=8, output_height=28, output_width=28,
                 n_input=784, n_hidden_layer_1=128,
                 z_dim=100, g_lr=8e-4, d_lr=8e-4, epsilon=1e-9):

        """
        # General Settings
        :param s: TF Session
        :param batch_size: training batch size, default 32
        :param input_height: input image height, default 28
        :param input_width: input image width, default 28
        :param channel: input image channel, default 1 (gray-scale)
        - in case of MNIST, image size is 28x28x1(HWC).
        :param n_classes: input dataset's classes
        - in case of MNIST, 10 (0 ~ 9)

        # Output Settings
        :param sample_num: the number of output images, default 64
        :param sample_size: sample image size, default 8
        :param output_height: output images height, default 28
        :param output_width: output images width, default 28

        # For DNN model
        :param n_input: input image size, default 784(28x28)
        :param n_hidden_layer_1: first NN hidden layer, default 128

        # Training Option
        :param z_dim: z dimension (kinda noise), default 100
        :param g_lr: generator learning rate, default 8e-4
        :param d_lr: discriminator learning rate, default 8e-4
        :param epsilon: epsilon, default 1e-9
        """

        self.s = s
        self.batch_size = batch_size

        self.input_height = input_height
        self.input_width = input_width
        self.channel = channel
        self.n_classes = n_classes

        self.sample_num = sample_num
        self.sample_size = sample_size
        self.output_height = output_height
        self.output_width = output_width

        self.n_input = n_input
        self.n_hl_1 = n_hidden_layer_1

        self.z_dim = z_dim
        self.d_lr, self.g_lr = d_lr, g_lr
        self.eps = epsilon

        ''' Weights

        - discriminator
        (784, 128) -> (128, 10)
        
        - generator
        (100, 128) -> (128, 784)
        
        Initializer : HE initializer
        '''
        self.W = {
            # for discriminator
            'd_h1': tf.get_variable('d_h1',
                                    shape=[self.n_input, self.n_hl_1],
                                    initializer=tf.contrib.layers.variance_scaling_initializer()),
            'd_h_out': tf.get_variable('d_h_out',
                                       shape=[self.n_hl_1, 1],
                                       initializer=tf.contrib.layers.variance_scaling_initializer()),
            # for generator
            'g_h1': tf.get_variable('g_h1',
                                    shape=[self.z_dim, self.n_hl_1],
                                    initializer=tf.contrib.layers.variance_scaling_initializer()),
            'g_h_out': tf.get_variable('g_h_out',
                                       shape=[self.n_hl_1, self.n_input],
                                       initializer=tf.contrib.layers.variance_scaling_initializer()),
        }

        ''' Biases
        
        - discriminator
        (128), (1)
        
        - generator
        (128), (784)
        
        Initializer : zero initializer
        '''
        self.b = {
            # for discriminator
            'd_b1': tf.Variable(tf.zeros([self.n_hl_1])),
            'd_b_out': tf.Variable(tf.zeros([1])),
            # for generator
            'g_b1': tf.Variable(tf.zeros([self.n_hl_1])),
            'g_b_out': tf.Variable(tf.zeros([self.n_input])),
        }

        '''
        self.batch = tf.Variable(0)
        self.opt = lambda x: tf.train.exponential_decay(
            learning_rate=x,
            global_step=self.batch,
            decay_rate=0.95,
            decay_steps=100,
            staircase=True
        )
        '''

        # Placeholder
        self.x = tf.placeholder(tf.float32, shape=[None, self.n_input], name="x-image")  # (-1, 784)
        self.z = tf.placeholder(tf.float32, shape=[None, self.z_dim], name='z-noise')    # (-1, 100)

        self.build_gan()  # build GAN model

    def discriminator(self, x, reuse=None):
        with tf.variable_scope("discriminator", reuse=reuse):
            net = tf.nn.bias_add(tf.matmul(x, self.W['d_h1']), self.b['d_b1'])
            net = tf.nn.leaky_relu(net)

            logits = tf.nn.bias_add(tf.matmul(net, self.W['d_h_out']), self.b['d_b_out'])
            # prob = tf.nn.sigmoid(logits)

        return logits

    def generator(self, z, reuse=None):
        with tf.variable_scope("generator", reuse=reuse):
            de_net = tf.nn.bias_add(tf.matmul(z, self.W['g_h1']), self.b['g_b1'])
            de_net = tf.nn.leaky_relu(de_net)

            logits = tf.nn.bias_add(tf.matmul(de_net, self.W['g_h_out']), self.b['g_b_out'])
            prob = tf.nn.sigmoid(logits)

        return prob

    def build_gan(self):
        # Generator
        self.g = self.generator(self.z)

        # Discriminator
        d_real = self.discriminator(self.x)
        d_fake = self.discriminator(self.g, reuse=True)

        # General GAN loss function referred in the paper
        """
        # Maximize log(D(G(z)))
        # Maximize log(D(x)) + log(1 - D(G(z)))

        log = lambda x: tf.log(x + self.eps)

        self.g_loss = -tf.reduce_mean(log(d_fake))
        self.d_loss = -tf.reduce_mean(log(d_real) + log(1. - d_fake))
        """

        # Softmax Loss
        # Z_B = sigma x∈B exp(−μ(x)), −μ(x) is discriminator
        z_b = tf.reduce_sum(tf.exp(-d_real)) + tf.reduce_sum(tf.exp(-d_fake)) + self.eps

        b_plus = self.batch_size
        b_minus = self.batch_size * 2

        # L_G = sigma x∈B+ μ(x)/abs(B) + sigma x∈B- μ(x)/abs(B) + ln(Z_B), B+ : batch _size
        self.g_loss = tf.reduce_sum(d_real / b_plus) + tf.reduce_sum(d_fake / b_minus) + tf.log(z_b)

        # L_D = sigma x∈B+ μ(x)/abs(B) + ln(Z_B), B+ : batch _size
        self.d_loss = tf.reduce_sum(d_real / b_plus) + tf.log(z_b)

        # Summary
        z_sum = tf.summary.histogram("z-noise", self.z)

        self.g = tf.reshape(self.g, shape=[-1, self.output_height, self.output_height, self.channel])
        g_sum = tf.summary.image("generated", self.g)  # generated images by Generative Model
        d_real_sum = tf.summary.histogram("d_real", d_real)
        d_fake_sum = tf.summary.histogram("d_fake", d_fake)
        d_loss_sum = tf.summary.scalar("d_loss", self.d_loss)
        g_loss_sum = tf.summary.scalar("g_loss", self.g_loss)

        # model saver
        self.saver = tf.train.Saver()

        # optimizer
        vars = tf.trainable_variables()
        d_params = [v for v in vars if v.name.startswith('d_')]
        g_params = [v for v in vars if v.name.startswith('g_')]

        self.d_op = tf.train.AdamOptimizer(self.d_lr).minimize(self.d_loss, var_list=d_params)
        self.g_op = tf.train.AdamOptimizer(self.g_lr).minimize(self.g_loss, var_list=g_params)

        # merge summary
        self.g_sum = tf.summary.merge([z_sum, d_fake_sum, g_sum, g_loss_sum])
        self.d_sum = tf.summary.merge([z_sum, d_real_sum, d_loss_sum])
        self.merged = tf.summary.merge_all()
        self.writer = tf.summary.FileWriter('./model/', self.s.graph)
