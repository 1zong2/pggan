from lib.options import BaseOptions


class TrainOptions(BaseOptions):
    
    def initialize(self):
        super().initialize()

        # Hyperparameters
        self.parser.add_argument('--batch_per_gpu', type=str, default=16)
        self.parser.add_argument('--max_step', type=str, default=1100000)
        self.parser.add_argument('--same_prob', type=float, default=0.2)

        # Dataset
        self.parser.add_argument('--dataset_root', type=str, \
            # default='/home/compu/exp/dataset/CelebAMask-HQ/CelebA-HQ-img')
            default='/home/leee/data/kface_front')

        # Learning rate
        self.parser.add_argument('--lr_G', type=str, default=1e-4)
        self.parser.add_argument('--lr_D', type=str, default=4e-5)
        self.parser.add_argument('--beta1', type=float, default=0)
        self.parser.add_argument('--beta2', type=float, default=0.99)

        # Weight
        self.parser.add_argument('--W_adv', type=float, default=1)
        self.parser.add_argument('--W_gp', type=float, default=10)
        self.parser.add_argument('--W_drift_D', type=float, default=0.001)

        # Model
        self.parser.add_argument('--latent_dim', type=int, default=512)
        self.parser.add_argument('--input_dim', type=int, default=3)
        self.parser.add_argument('--output_dim', type=int, default=3)
        self.parser.add_argument('--init_bias_to_zero', type=bool, default=True)
        
        self.parser.add_argument('--depths', type=list, \
            # default=[512, 512, 512, 512, 256, 128, 64, 32, 16]) # 1024 x 1024
            default=[512, 512, 512, 512, 256, 128, 64]) # 256 x 256
        self.parser.add_argument('--max_depths', type=int, \
            # default=9)
            default=7)

        ## Scale
        # self.parser.add_argument('--scale_index', type=int, default=0)
        self.parser.add_argument('--max_step_at_scale', type=list, \
            # default=[48000, 96000, 96000, 96000, 96000, 96000, 96000, 96000, 200000])
            default=[48000, 96000, 96000, 96000, 96000, 96000, 150000, 200000, 200000])
        
        ## Alpha
        self.parser.add_argument('--alpha', type=float, default=0)
        self.parser.add_argument('--alpha_jump_start', type=int, default=[0, 500, 500, 500, 500, 500, 500, 500, 500])
        self.parser.add_argument('--alpha_jump_interval', type=int, default=[0, 32, 32, 32, 32, 32, 32, 32, 32])
        self.parser.add_argument('--alpha_jump_Ntimes', type=int, default=[0, 600, 600, 600, 600, 600, 600, 600, 600])
        
        ## Activation
        self.parser.add_argument('--LReLU_slope', type=float, default=0.2)
        self.parser.add_argument('--generator_last_activation', default=None) # linear function as default

        ## Normalization        
        self.parser.add_argument('--apply_pixel_norm', type=bool, default=True)
        self.parser.add_argument('--apply_minibatch_norm', type=bool, default=True)
        
        self.parser.add_argument('--equalized_lr', type=bool, default=True)
        
        self.parser.add_argument('--decision_layer_size', type=int, default=1)


class TestOptions(BaseOptions):
    
    def initialize(self):

        # GPU
        self.parser.add_argument('--gpu', type=int, default=0)
        
        # Sample Generation
        self.parser.add_argument('--n_samples', type=int, default=10)
        self.parser.add_argument('--save_path', type=str, default='./test_result')
        
        # Model
        self.parser.add_argument('--ckpt_path', type=str, default='train_result/fb_w_gp/ckpt/G_latest.pt')

        self.parser.add_argument('--latent_dim', type=int, default=512)
        self.parser.add_argument('--input_dim', type=int, default=3)
        self.parser.add_argument('--output_dim', type=int, default=3)
        self.parser.add_argument('--init_bias_to_zero', type=bool, default=True)
        
        self.parser.add_argument('--depths', type=list, \
            # default=[512, 512, 512, 512, 256, 128, 64, 32, 16]) # 1024 x 1024
            # default=[512, 512, 512, 512, 256, 128, 64]) # 256 x 256
            default=[512, 512, 512, 512, 256, 128]) # 128 x 128 current ckpt is not complete
    
        ## Activation
        self.parser.add_argument('--LReLU_slope', type=float, default=0.2)
        self.parser.add_argument('--generator_last_activation', default=None) # linear function as default

        ## Normalization        
        self.parser.add_argument('--apply_pixel_norm', type=bool, default=True)

        self.parser.add_argument('--equalized_lr', type=bool, default=True)
      