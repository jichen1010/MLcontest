import matplotlib

matplotlib.use('Agg')
import numpy as np  # linear algebra
import pandas as pd  # data processing, CSV file I/O (e.g. pd.read_csv)

np.random.seed(1234)
import torch
from torch.autograd import Variable
from imageio import imread, imsave
from torch.nn import functional as F
from torch.nn import init
from skimage.morphology import label
import matplotlib.pyplot as plt
import sys
import os
import pickle
import torch.random

# ouputs number; epochs; initial learning rate; learning rate decay pace
output = sys.argv[1]
eps = sys.argv[2]
LR = sys.argv[3]
lr_decay = sys.argv[4]

if not os.path.exists('../' + output):
    os.makedirs('../' + output)

# Use cuda or not (use GPU or CPU)
USE_CUDA = 1


# Image cutter (cut to 256x256); input an image, return an array of cutted images and original image dimention
def minicut(im):
    imdim = (im.shape[-2], im.shape[-1])
    minilist = []
    num1 = int(im.shape[-2] / 256)
    num2 = int(im.shape[-1] / 256)
    for co in range(num1):
        for ro in range(num2):
            mini = im[0, :, co * 256:(co + 1) * 256, ro * 256:(ro + 1) * 256]
            minilist.append(mini)
    minilist = np.array(minilist)
    return minilist, imdim


# Data loader for training; if we have stored images in a pickle file, just read it; otherwise, we make a pickle.
# Training images will be augmented by this function, validation and test images won't.
# handles is a list made during preprocessing contains all paths to images and original image dimensions.
# note that these images loaded here have already been padded to shapes of multiples of 256x256 during preprocessing
def dataloader(handles, mode='train'):
    try:
        with open('../inputs/cropped/' + mode + '.pickle', 'rb') as f:
            images = pickle.load(f)
    except:
        images = {}
        images['Image'] = []
        images['Label'] = []
        images['ID'] = []
        images['Dim'] = []
        # itterate over handles
        for idx, row in handles.iterrows():
            # read a image
            im = imread(row['Image'])
            # normalize image
            im = im / im.max() * 255
            im_aug = []
            shape = im.shape[0]
            # training images got augmented
            if mode == 'train':
                ima = np.rot90(im)
                imb = np.rot90(ima)
                imc = np.rot90(imb)
                imd = np.fliplr(im)
                ime = np.flipud(im)
            # reshape image for conversion to tensor
            image = np.empty((3, shape, shape), dtype='float32')
            for i in range(3):
                image[i, :, :] = im[:, :, i]
            im = image
            im_aug.append(im)
            # reshape for training augmented images
            if mode == 'train':
                for i in range(3):
                    image[i, :, :] = ima[:, :, i]
                ima = image
                for i in range(3):
                    image[i, :, :] = imb[:, :, i]
                imb = image
                for i in range(3):
                    image[i, :, :] = imc[:, :, i]
                imc = image
                for i in range(3):
                    image[i, :, :] = imd[:, :, i]
                imd = image
                for i in range(3):
                    image[i, :, :] = ime[:, :, i]
                ime = image
                im_aug.append(ima)
                im_aug.append(imb)
                im_aug.append(imc)
                im_aug.append(imd)
                im_aug.append(ime)
            # save images to a list
            images['Image'].append(np.array(im_aug))

            # For training and validation images, we should do same thing for labels (ground truth masks)
            if mode != 'test':
                la_aug = []
                la = imread(row['Label'])
                if mode == 'train':
                    laa = np.rot90(la)
                    lab = np.rot90(laa)
                    lac = np.rot90(lab)
                    lad = np.fliplr(la)
                    lae = np.flipud(la)
                la = np.reshape(la, [1, la.shape[0], la.shape[1]])
                la_aug.append(la)
                if mode == 'train':
                    laa = np.reshape(laa, [1, laa.shape[0], laa.shape[1]])
                    lab = np.reshape(lab, [1, lab.shape[0], lab.shape[1]])
                    lac = np.reshape(lac, [1, lac.shape[0], lac.shape[1]])
                    lad = np.reshape(lad, [1, lad.shape[0], lad.shape[1]])
                    lae = np.reshape(lae, [1, lae.shape[0], lae.shape[1]])
                    la_aug.append(laa)
                    la_aug.append(lab)
                    la_aug.append(lac)
                    la_aug.append(lad)
                    la_aug.append(lae)
                images['Label'].append(np.array(la_aug))

            # Save original dimension of test images
            elif mode == 'test':
                images['Dim'].append([(row['Width'], row['Height'])])
            images['ID'].append(row['ID'])
        # save all things to a pickle file and loaded it to return
        with open("../inputs/cropped/" + mode + '.pickle', 'wb') as f:
            pickle.dump(images, f)
        with open('../inputs/cropped/' + mode + '.pickle', 'rb') as f:
            images = pickle.load(f)
    return images


## Main U-net model
# Down sampling phase layers
class UNet_down_block(torch.nn.Module):
    def __init__(self, input_channel, output_channel, down_size):
        super(UNet_down_block, self).__init__()
        self.conv1 = torch.nn.Conv2d(input_channel, output_channel, 3, padding=1)
        self.bn1 = torch.nn.BatchNorm2d(output_channel)
        self.conv2 = torch.nn.Conv2d(output_channel, output_channel, 3, padding=1)
        self.bn2 = torch.nn.BatchNorm2d(output_channel)
        self.conv3 = torch.nn.Conv2d(output_channel, output_channel, 3, padding=1)
        self.bn3 = torch.nn.BatchNorm2d(output_channel)
        self.max_pool = torch.nn.MaxPool2d(2, 2)
        self.relu = torch.nn.ReLU()
        self.down_size = down_size

    def forward(self, x):
        if self.down_size:
            x = self.max_pool(x)
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.relu(self.bn2(self.conv2(x)))
        x = self.relu(self.bn3(self.conv3(x)))
        return x


# Up sampling phase layers
class UNet_up_block(torch.nn.Module):
    def __init__(self, prev_channel, input_channel, output_channel):
        super(UNet_up_block, self).__init__()
        self.up_sampling = torch.nn.Upsample(scale_factor=2, mode='bilinear')
        self.conv1 = torch.nn.Conv2d(prev_channel + input_channel, output_channel, 3, padding=1)
        self.bn1 = torch.nn.BatchNorm2d(output_channel)
        self.conv2 = torch.nn.Conv2d(output_channel, output_channel, 3, padding=1)
        self.bn2 = torch.nn.BatchNorm2d(output_channel)
        self.conv3 = torch.nn.Conv2d(output_channel, output_channel, 3, padding=1)
        self.bn3 = torch.nn.BatchNorm2d(output_channel)
        self.relu = torch.nn.ReLU()

    def forward(self, prev_feature_map, x):
        x = self.up_sampling(x)
        x = torch.cat((x, prev_feature_map), dim=1)
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.relu(self.bn2(self.conv2(x)))
        x = self.relu(self.bn3(self.conv3(x)))
        return x


# Put them together and build the model to use
class UNet(torch.nn.Module):
    def __init__(self):
        super(UNet, self).__init__()

        self.down_block1 = UNet_down_block(3, 16, False)
        self.down_block2 = UNet_down_block(16, 32, True)
        self.down_block3 = UNet_down_block(32, 64, True)
        self.down_block4 = UNet_down_block(64, 128, True)
        self.down_block5 = UNet_down_block(128, 256, True)
        self.down_block6 = UNet_down_block(256, 512, True)
        self.down_block7 = UNet_down_block(512, 1024, True)

        self.mid_conv1 = torch.nn.Conv2d(1024, 1024, 3, padding=1)
        self.bn1 = torch.nn.BatchNorm2d(1024)
        self.mid_conv2 = torch.nn.Conv2d(1024, 1024, 3, padding=1)
        self.bn2 = torch.nn.BatchNorm2d(1024)
        self.mid_conv3 = torch.nn.Conv2d(1024, 1024, 3, padding=1)
        self.bn3 = torch.nn.BatchNorm2d(1024)

        self.up_block1 = UNet_up_block(512, 1024, 512)
        self.up_block2 = UNet_up_block(256, 512, 256)
        self.up_block3 = UNet_up_block(128, 256, 128)
        self.up_block4 = UNet_up_block(64, 128, 64)
        self.up_block5 = UNet_up_block(32, 64, 32)
        self.up_block6 = UNet_up_block(16, 32, 16)

        self.last_conv1 = torch.nn.Conv2d(16, 16, 3, padding=1)
        self.last_bn = torch.nn.BatchNorm2d(16)
        self.last_conv2 = torch.nn.Conv2d(16, 1, 1, padding=0)
        self.relu = torch.nn.ReLU()

    def forward(self, x):
        self.x1 = self.down_block1(x)
        self.x2 = self.down_block2(self.x1)
        self.x3 = self.down_block3(self.x2)
        self.x4 = self.down_block4(self.x3)
        self.x5 = self.down_block5(self.x4)
        self.x6 = self.down_block6(self.x5)
        self.x7 = self.down_block7(self.x6)
        self.x7 = self.relu(self.bn1(self.mid_conv1(self.x7)))
        self.x7 = self.relu(self.bn2(self.mid_conv2(self.x7)))
        self.x7 = self.relu(self.bn3(self.mid_conv3(self.x7)))
        x = self.up_block1(self.x6, self.x7)
        x = self.up_block2(self.x5, x)
        x = self.up_block3(self.x4, x)
        x = self.up_block4(self.x3, x)
        x = self.up_block5(self.x2, x)
        x = self.up_block6(self.x1, x)
        x = self.relu(self.last_bn(self.last_conv1(x)))
        x = self.last_conv2(x)
        return x


# Initial weights for the model
def init_weights(module):
    for name, param in module.named_parameters():
        if name.find('weight') != -1:
            if len(param.size()) == 1:
                Cuda(init.uniform(param.data, 1).type(torch.DoubleTensor))
            else:
                Cuda(init.xavier_uniform(param.data).type(torch.DoubleTensor))
        elif name.find('bias') != -1:
            Cuda(init.constant(param.data, 0).type(torch.DoubleTensor))


# Convert variables to GPU compatible version function (ignore the red-line error because I assume your computer don't
# have cuda model to use GPU alone)
def Cuda(obj):
    if USE_CUDA:
        if isinstance(obj, tuple):
            return tuple(cuda(o) for o in obj)
        elif isinstance(obj, list):
            return list(cuda(o) for o in obj)
        elif hasattr(obj, 'cuda'):
            return obj.cuda()
    return obj


# Convert the test image output masks back to its original dimension after the U-net model
def back_scale(model_im, im_shape):
    temp = np.reshape(model_im, [model_im.shape[-2], model_im.shape[-1]])
    row_size_left = (temp.shape[0] - im_shape[0][1]) // 2
    row_size_right = (temp.shape[0] - im_shape[0][1]) // 2 + (temp.shape[0] - im_shape[0][1]) % 2
    col_size_left = (temp.shape[1] - im_shape[0][0]) // 2
    col_size_right = (temp.shape[1] - im_shape[0][0]) // 2 + (temp.shape[1] - im_shape[0][0]) % 2
    if row_size_right == 0 and col_size_right == 0:
        new_im = temp[row_size_left:, col_size_left:]
    elif row_size_right == 0:
        new_im = temp[row_size_left:, col_size_left:-col_size_right]
    elif col_size_right == 0:
        new_im = temp[row_size_left:-row_size_right, col_size_left:]
    else:
        new_im = temp[row_size_left:-row_size_right, col_size_left:-col_size_right]
    return new_im


# For contest csv conversion only
def rle_encoding(x):
    dots = np.where(x.T.flatten() == 1)[0]
    run_lengths = []
    prev = -2
    for b in dots:
        if (b > prev + 1): run_lengths.extend((b + 1, 0))
        run_lengths[-1] += 1
        prev = b
    return run_lengths


# For contest csv conversion only
def prob_to_rles(x, cutoff=0.5):
    lab_img = label(x > cutoff)
    for i in range(1, lab_img.max() + 1):
        yield rle_encoding(lab_img == i)


# For contest evaluation only
def metric(y_pred, target):
    pred_vec = y_pred.view(-1).data.numpy()
    target_vec = target.view(-1).data.numpy()
    label = target_vec.sum()
    pred = (pred_vec > 0.5).astype(np.uint8)
    tp = (pred * target_vec).sum()
    predicted = pred.sum()
    ppv = (tp + 1) / (predicted + label - tp + 1)
    return ppv


## Main training function
# bs is batch size, which is 1 in our case
# sample and vasample are lists containing paths to padded training and validation images and their original dimensions
# ep is training epoch number
def train(bs, sample, vasample, ep, ilr, lr_dec):
    # initial learning rate
    init_lr = ilr
    # Load u-net model
    model = Cuda(UNet())
    # initial model weights
    init_weights(model)
    # set up optimizer (use Adam optimizer)
    opt = torch.optim.Adam(model.parameters(), lr=init_lr)
    opt.zero_grad()
    # Get numbers of training and validation samples
    rows_trn = len(sample['Label'])
    rows_val = len(vasample['Label'])
    # batch per epoch
    batches_per_epoch = rows_trn // bs
    losslists = []
    vlosslists = []

    for epoch in range(ep):
        # Learning rate determination based on learning rate decay pace
        lr = init_lr * (0.1 ** (epoch // lr_dec))
        order = np.arange(rows_trn)
        losslist = []
        tr_metric_list = []
        va_metric_list = []
        for itr in range(batches_per_epoch):
            # load a batch of images (1 image per batch in our case)
            rows = order[itr * bs: (itr + 1) * bs]
            if itr + 1 == batches_per_epoch:
                rows = order[itr * bs:]
            # read in a batch
            trim = sample['Image'][rows[0]]
            trla = sample['Label'][rows[0]]
            # load augmented and original image of this batch (6 images in our case)
            for iit in range(6):
                trimm = trim[iit:iit + 1, :, :, :]
                trlaa = trla[iit:iit + 1, :, :, :]
                # cut images to 256x256 small images
                minitrlist, trimmdim = minicut(trimm)
                minilalist, trlaadim = minicut(trlaa)
                # load each 256x256 small image
                for iiit in range(minitrlist.shape[0]):
                    xxx = minitrlist[iiit:iiit + 1, :, :, :]
                    yyy = minilalist[iiit:iiit + 1, :, :, :]
                    # Get positive/negative ratio in that image, 1 means balanced, 0 means no positive in that image.
                    label_ratio = (yyy > 0).sum() / (
                            yyy.shape[1] * yyy.shape[2] * yyy.shape[3] - (yyy > 0).sum())
                    # adjust weights based on the ratio
                    if label_ratio < 1 and label_ratio > 0:
                        add_weight = (yyy[0, 0, :, :] / 255 + 1 / (1 / label_ratio - 1)) * 100
                        loss_fn = torch.nn.BCEWithLogitsLoss(
                            weight=Cuda(torch.from_numpy(add_weight).type(torch.FloatTensor)))
                    elif label_ratio > 1:
                        add_weight = (yyy[0, 0, :, :] / 255 + 1 / (label_ratio - 1)) * 100
                        loss_fn = torch.nn.BCEWithLogitsLoss(
                            weight=Cuda(torch.from_numpy(add_weight).type(torch.FloatTensor)))
                    elif label_ratio == 1 or label_ratio == 0:
                        loss_fn = torch.nn.BCEWithLogitsLoss()
                    # Load image to GPU
                    x = Cuda(Variable(torch.from_numpy(xxx).type(torch.FloatTensor)))
                    # Load label to GPU
                    yyy = Cuda(Variable(torch.from_numpy(yyy / 255).type(torch.FloatTensor)))
                    # Predict using u-net
                    pred_mask = model(x)
                    # Calculate loss of prediction
                    loss = loss_fn(pred_mask, yyy)
                    # save loss
                    losslist.append(loss.cpu().data.numpy()[0])
                    loss.backward()
                    # (For contest only)
                    tr_metric = metric(F.sigmoid(pred_mask.cpu()), yyy.cpu())
                    tr_metric_list.append(tr_metric)

        vlosslist = []
        # Do the same thing for validation set
        for itr in range(rows_val):
            vaim = vasample['Image'][itr]
            vala = vasample['Label'][itr]
            for iit in range(1):
                vaimm = vaim[iit:iit + 1, :, :, :]
                valaa = vala[iit:iit + 1, :, :, :]

                minivalist, vaimmdim = minicut(vaimm)
                vminilalist, valaadim = minicut(valaa)
                for iiit in range(minivalist.shape[0]):
                    xxx = minivalist[iiit:iiit + 1, :, :, :]
                    yyy = vminilalist[iiit:iiit + 1, :, :, :]
                    label_ratio = (yyy > 0).sum() / (
                            yyy.shape[1] * yyy.shape[2] * yyy.shape[3] - (yyy > 0).sum())
                    if label_ratio < 1 and label_ratio > 0:
                        add_weight = (yyy[0, 0, :, :] / 255 + 1 / (1 / label_ratio - 1)) * 100
                        loss_fn = torch.nn.BCEWithLogitsLoss(
                            weight=Cuda(torch.from_numpy(add_weight).type(torch.FloatTensor)))
                    elif label_ratio > 1:
                        add_weight = (yyy[0, 0, :, :] / 255 + 1 / (label_ratio - 1)) * 100
                        loss_fn = torch.nn.BCEWithLogitsLoss(
                            weight=Cuda(torch.from_numpy(add_weight).type(torch.FloatTensor)))
                    elif label_ratio == 1 or label_ratio == 0:
                        loss_fn = torch.nn.BCEWithLogitsLoss()
                    x = Cuda(Variable(torch.from_numpy(xxx).type(torch.FloatTensor)))
                    yyy = Cuda(Variable(torch.from_numpy(yyy / 255).type(torch.FloatTensor)))
                    pred_maskv = model(x)  # .cpu() # .round()
                    vloss = loss_fn(pred_maskv, yyy)
                    vlosslist.append(vloss.cpu().data.numpy()[0])
                    vloss.backward()
                    va_metric = metric(F.sigmoid(pred_maskv.cpu()), yyy.cpu())
                    va_metric_list.append(va_metric)

        # Calculate average loss of this epoch
        lossa = np.mean(losslist)
        vlossa = np.mean(vlosslist)
        tr_score = np.mean(tr_metric_list)
        va_score = np.mean(va_metric_list)
        print(
            'Epoch {:>3} |lr {:>1.5f} | Loss {:>1.5f} | VLoss {:>1.5f} | Train Score {:>1.5f} | Val Score {:>1.5f} '.format(
                epoch + 1, lr, lossa, vlossa, tr_score, va_score))
        # optimize model based on what learned in this epoch
        opt.step()
        opt.zero_grad()
        losslists.append(lossa)
        vlosslists.append(vlossa)

        # adjust learning rate
        for param_group in opt.param_groups:
            param_group['lr'] = lr
        # save model every 10 epoch
        if (epoch + 1) % 10 == 0:
            checkpoint = {
                'epoch': epoch + 1,
                'state_dict': model.state_dict(),
                'optimizer': opt.state_dict(),
            }
            torch.save(checkpoint, '../' + output + '/unet-{}'.format(epoch + 1))

        # early stopping: after the 10th epoch, if loss gets worse or stay the same for 5 consecutive epochs, stop training
        # to avoid overfitting
        if epoch > 10:
            if losslists[-1] >= losslists[-2] and losslists[-2] >= losslists[-3] and losslists[-3] >= losslists[-4] and \
                    losslists[-4] >= losslists[-5]:
                break
            elif vlosslists[-1] >= vlosslists[-2] and vlosslists[-2] >= vlosslists[-3] and vlosslists[-3] >= vlosslists[
                -4] and vlosslists[-4] >= vlosslists[-5]:
                break

    # Loss figures
    plt.plot(losslists)
    plt.plot(vlosslists)
    plt.title('Train & Validation Loss')
    plt.legend(['Train', 'Validation'], loc='upper right')
    plt.savefig('../' + output + '/loss.png')
    return model


## Main function for testing
# tesample is a list containing paths to padded testing images and their original dimensions
# model is trained model
def test(tesample, model, group):
    test_ids = []
    rles = []
    # output folder
    if not os.path.exists('../' + output + '/' + group):
        os.makedirs('../' + output + '/' + group)
    for itr in range(len(tesample['ID'])):
        # load testing image, ID, and dimension
        teim = tesample['Image'][itr]
        teid = tesample['ID'][itr]
        tedim = tesample['Dim'][itr]
        xt = Cuda(Variable(torch.from_numpy(teim).type(torch.FloatTensor)))
        # predict mask
        pred_mask = model(xt)
        # Binarize mask for output
        pred_np = (F.sigmoid(pred_mask) > 0.5).cpu().data.numpy().astype(np.uint8)
        pred_np = back_scale(pred_np, tedim)
        imsave('../' + output + '/' + group + '/' + teid + '_pred.png', ((pred_np/pred_np.max())*255).astype(np.uint8))
        # For contest only
        rle = list(prob_to_rles(pred_np))
        rles.extend(rle)
        test_ids.extend([teid] * len(rle))
    # For contest only
    sub = pd.DataFrame()
    sub['ImageId'] = test_ids
    sub['EncodedPixels'] = pd.Series(rles).apply(lambda x: ' '.join(str(y) for y in x))

## Main
# Read csv files containing paths to padded images and their original dimensions
tr = pd.read_csv('../inputs/stage_1_train/samples.csv', header=0,
                 usecols=['Image', 'Label', 'Width', 'Height', 'ID'])
va = pd.read_csv('../inputs/stage_1_test/vsamples.csv', header=0,
                 usecols=['Image', 'Label', 'Width', 'Height', 'ID'])
te = pd.read_csv('../inputs/stage_2_test/samples.csv', header=0, usecols=['Image', 'ID', 'Width', 'Height'])

# Load/make data
trsample = dataloader(tr, 'train')
vasample = dataloader(va, 'val')
tebsample = dataloader(te, 'test')

# Training
model = train(1, trsample, vasample, int(eps), float(LR), int(lr_decay))
# Predict masks for testing set
tebsub = test(tebsample, model, 'stage_2_test')
# Contest only csv output
tebsub.to_csv('../' + output + '/stage_2_test_sub.csv', index=False)





# from skimage import color
# img = color.rgb2gray(io.imread('image.png'))
# from skimage import util
# inverted_img = util.invert(img)