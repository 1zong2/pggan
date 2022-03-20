import torch
from torch import nn
import torch.nn.functional as F

from lib.utils import num_flat_features
from lib.blocks import ProgressiveGeneratorBlock, ProgressiveDiscriminatorBlock, LastProgressiveDiscriminatorBlock, toRGBBlock, fromRGBBlock
from lib.layers import EqualizedLinear, PixelwiseVectorNorm

class Generator(nn.Module):
    
    def __init__(self,
                 latent_dim,
                 first_depth,
                 initBiasToZero=True,
                 LReLU_slope=0.2,
                 apply_pixel_norm=True,
                 generationActivation=None,
                 output_dim=3,
                 equalizedlR=True):
        r"""
        Build a generator for a progressive GAN model
        Args:
            - dimLatent (int): dimension of the latent vector
            - depthScale0 (int): depth of the lowest resolution scales
            - initBiasToZero (bool): should we set the bias to zero when a
                                    new scale is added
            - leakyReluLeak (float): leakyness of the leaky relu activation
                                    function
            - normalization (bool): normalize the input latent vector
            - generationActivation (function): activation function of the last
                                               layer (RGB layer). If None, then
                                               the identity is used
            - dimOutput (int): dimension of the output image. 3 -> RGB, 1 ->
                               grey levels
            - equalizedlR (bool): set to true to initiualize the layers with
                                  N(0,1) and apply He's constant at runtime
        """
        super(Generator, self).__init__()

        self.equalizedlR = equalizedlR
        self.initBiasToZero = initBiasToZero

        # Leaky relu activation
        self.leakyRelu = torch.nn.LeakyReLU(LReLU_slope)

        # normalization
        self.apply_pixel_norm = apply_pixel_norm
        self.pixel_norm = None
        if apply_pixel_norm:
            self.pixel_norm = PixelwiseVectorNorm()

        # Initalize the blocks
        self.block_depths = [first_depth]
        self.first_depth = first_depth
        self.blocks = nn.ModuleList()
        self.toRGB_blocks = nn.ModuleList()

        # Initialize the block 0
        self.init_format_layer(latent_dim)
        self.output_dim = output_dim
        self.first_block = ProgressiveGeneratorBlock(first_depth, first_depth, 
                                                 equalizedlR=self.equalizedlR,
                                                 initBiasToZero=self.initBiasToZero, 
                                                 norm=self.pixel_norm, 
                                                 is_first=True)

        self.toRGB_blocks.append(toRGBBlock(first_depth, 
                                            output_dim=self.output_dim, 
                                            equalizedlR=self.equalizedlR, 
                                            initBiasToZero=self.initBiasToZero))

        # Initalize the upscaling parameters
        # alpha : when a new scale is added to the network, the previous
        # layer is smoothly merged with the output in the first stages of
        # the training
        self.alpha = 0

        # Last layer activation function
        self.generationActivation = generationActivation
        


    def init_format_layer(self, latent_dim):
        r"""
        The format layer represents the first weights applied to the latent
        vector. It converts a 1xdimLatent input into a 4 x 4 xscalesDepth[0]
        layer.
        """

        self.latent_dim = latent_dim
        self.latent_format_layer = EqualizedLinear(self.latent_dim,
                                                    16 * self.first_depth,
                                                    initBiasToZero=self.initBiasToZero)

    def get_output_size(self):
        r"""
        Get the size of the generated image.
        """
        side = 4 * (2**(len(self.toRGBLayers) - 1))
        return (side, side)

    def add_block(self, new_depth):
        r"""
        Add a new scale to the model. Increasing the output resolution by
        a factor 2
        Args:
            - depthNewScale (int): depth of each conv layer of the new scale
        """
        prev_depth = self.block_depths[-1]

        self.block_depths.append(new_depth)
        self.blocks.append(ProgressiveGeneratorBlock(prev_depth, new_depth, 
                                                     equalizedlR=self.equalizedlR,
                                                     initBiasToZero=self.initBiasToZero, 
                                                     norm=self.pixel_norm))
        self.toRGB_blocks.append(toRGBBlock(new_depth, 
                                            output_dim=self.output_dim, 
                                            equalizedlR=self.equalizedlR, 
                                            initBiasToZero=self.initBiasToZero))

    def set_new_alpha(self, alpha):
        r"""
        Update the value of the merging factor alpha
        Args:
            - alpha (float): merging factor, must be in [0, 1]
        """
        
        if alpha < 0 or alpha > 1:
            raise ValueError("alpha must be in [0,1]")

        if not self.toRGB_blocks:
            raise AttributeError("Can't set an alpha layer if only the scale 0"
                                 "is defined")

        self.alpha = alpha

    def forward(self, x):
        # print(">> G input", x.shape)

        ## Normalize the input ? ### ????
        if self.apply_pixel_norm:
            x = self.pixel_norm(x)
        x = x.view(-1, num_flat_features(x)) # 1 x N
        # format layer
        x = self.leakyRelu(self.latent_format_layer(x))
        x = x.view(x.size()[0], -1, 4, 4)

        if self.apply_pixel_norm:
            x = self.pixel_norm(x)

        # First block (no upsampling)
        x = self.first_block(x)

        # To RGB 
        # If there are 2 blocks and blending is required (alpha > 0)
        if self.alpha > 0 and len(self.blocks) == 1:
            x_prev = self.toRGB_blocks[-2](x, apply_upscale=True)

        # Upper scales
        for i, block in enumerate(self.blocks, 0):
            x = block(x)
            # print(">> intermediates", i, x.shape)
            # To RGB
            # If there are more than 2 blocks blending is required (alpha > 0)
            if self.alpha > 0 and i == (len(self.blocks) - 2):
                x_prev = self.toRGB_blocks[-2](x, apply_upscale=True)

        # To RGB (no alpha parameter for now)
        x = self.toRGB_blocks[-1](x)
        # print(">> G output", x.shape)

        # Blending with the lower resolution output when alpha > 0
        if self.alpha > 0:
            x = self.alpha * x_prev + (1.0 - self.alpha) * x

        if self.generationActivation is not None:
            x = self.generationActivation(x)

        return x


class Discriminator(nn.Module):

    def __init__(self,
                 last_depth,
                 initBiasToZero=True,
                 LReLU_slope=0.2,
                 decision_layer_size=1,
                 apply_minibatch_norm=False,
                 input_dim=3,
                 equalizedlR=True):
        r"""
        Build a discriminator for a progressive GAN model
        Args:
            - depthScale0 (int): depth of the lowest resolution scales
            - initBiasToZero (bool): should we set the bias to zero when a
                                    new scale is added
            - leakyReluLeak (float): leakyness of the leaky relu activation
                                    function
            - decisionActivation: activation function of the decision layer. If
                                  None it will be the identity function.
                                  For the training stage, it's advised to set
                                  this parameter to None and handle the
                                  activation function in the loss criterion.
            - sizeDecisionLayer: size of the decision layer. Will typically be
                                 greater than 2 when ACGAN is involved
            - miniBatchNormalization: do we apply the mini-batch normalization
                                      at the last scale ?
            - dimInput (int): 3 (RGB input), 1 (grey-scale input)
        """
        super(Discriminator, self).__init__()

        # Initialization paramneters
        self.initBiasToZero = initBiasToZero
        self.equalizedlR = equalizedlR
        self.input_dim = input_dim

        # Initalize the scales
        self.depths = [last_depth]
        self.blocks = nn.ModuleList()
        self.fromRGB_blocks = nn.ModuleList()

        self.mergeLayers = nn.ModuleList()

        # Initialize the last layer
        self.init_decision_layer(decision_layer_size)

        # Minibatch standard deviation
        self.apply_minibatch_norm = apply_minibatch_norm

        # Perform Minibatch normalization
        self.minibatch_normalization_block = LastProgressiveDiscriminatorBlock(last_depth,
                                                            equalizedlR=equalizedlR, initBiasToZero=initBiasToZero,
                                                            apply_minibatch_norm=apply_minibatch_norm)
        self.fromRGB_blocks.append(fromRGBBlock(input_dim, last_depth,
                                                equalizedlR=equalizedlR,
                                                initBiasToZero=initBiasToZero))

        # Initalize the upscaling parameters
        self.alpha = 0

        # Leaky relu activation
        self.leakyRelu = torch.nn.LeakyReLU(LReLU_slope)

    def add_block(self, new_depth):

        prev_depth = self.depths[-1]
        self.depths.append(new_depth)

        self.blocks.append(ProgressiveDiscriminatorBlock(new_depth, prev_depth,
                                                         equalizedlR=self.equalizedlR, 
                                                         initBiasToZero=self.initBiasToZero))

        self.fromRGB_blocks.append(fromRGBBlock(self.input_dim,
                                                  new_depth,
                                                  equalizedlR=self.equalizedlR,
                                                  initBiasToZero=self.initBiasToZero))

    def set_new_alpha(self, alpha):
        r"""
        Update the value of the merging factor alpha
        Args:
            - alpha (float): merging factor, must be in [0, 1]
        """

        if alpha < 0 or alpha > 1:
            raise ValueError("alpha must be in [0,1]")

        if not self.fromRGB_blocks:
            raise AttributeError("Can't set an alpha layer if only the scale 0"
                                 "is defined")

        self.alpha = alpha

    def init_decision_layer(self, decision_layer_size):

        self.decision_layer = EqualizedLinear(self.depths[0],
                                             decision_layer_size,
                                             equalized=self.equalizedlR,
                                             initBiasToZero=self.initBiasToZero)

    def forward(self, x, get_feature = False):
        # print(">> D input", x.shape) # (8, 3, 256, 256)
        # print(self) # show the structure of Discriminator

        # Alpha blending
        if self.alpha > 0 and len(self.fromRGB_blocks) > 1:
            y = self.fromRGB_blocks[-2](x, apply_downscale=True)

        # From RGB layer
        x = self.fromRGB_blocks[-1](x)

        # Caution: we must explore the layers group in reverse order !
        # Explore all scales before 0
        apply_merge = self.alpha > 0 and len(self.blocks) > 1
        for block in reversed(self.blocks):
            x = block(x)

            if apply_merge:
                apply_merge = False
                x = self.alpha * y + (1 - self.alpha) * x

        # Minibatch standard deviation
        x = self.minibatch_normalization_block(x)

        # last layer
        out = self.decision_layer(x)

        if not get_feature:
            return out

        return out, x