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

output = sys.argv[1]
eps = sys.argv[2]
LR = sys.argv[3]
lr_decay = sys.argv[4]

if not os.path.exists('../' + output):
    os.makedirs('../' + output)

# Use cuda or not
USE_CUDA = 1



def minicut(im):
    imdim = (im.shape[-2], im.shape[-1])
    minilist = []
    num1 = int(im.shape[-2]/256)
    num2 = int(im.shape[-1]/256)
    for co in range(num1):
        for ro in range(num2):
            mini = im[0,:,co*256:(co+1)*256,ro*256:(ro+1)*256]
            minilist.append(mini)
    minilist = np.array(minilist)
    return minilist, imdim


def dataloader(handles, mode = 'train'):
    try:
        with open('../inputs/cropped/' + mode + '.pickle', 'rb') as f:
            images = pickle.load(f)
    except:
        images = {}
        images['Image'] = []
        images['Label'] = []
        images['ID'] = []
        images['Dim'] = []
        for idx, row in handles.iterrows():
            im = imread(row['Image'])
            im = im / im.max() * 255
            im_aug = []
            shape = im.shape[0]
            if mode == 'train':
                ima = np.rot90(im)
                imb = np.rot90(ima)
                imc = np.rot90(imb)
                imd = np.fliplr(im)
                ime = np.flipud(im)
            image = np.empty((3, shape, shape), dtype='float32')
            for i in range(3):
                image[i,:,:] = im[:,:,i]
            im = image
            im_aug.append(im)
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
            images['Image'].append(np.array(im_aug))

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

            elif mode == 'test':
                images['Dim'].append([(row['Width'], row['Height'])])
            images['ID'].append(row['ID'])

        with open("../inputs/cropped/" + mode + '.pickle', 'wb') as f:
            pickle.dump(images, f)
        with open('../inputs/cropped/' + mode + '.pickle', 'rb') as f:
            images = pickle.load(f)
    return images

# def reader(list, mode='va'):
#     labellist = []
#     imlist = []
#     for index, row in list.iterrows():
#         name = row['Image']
#         im = imread(name)
#         im = im / im.max() * 255
#         if mode == 'tr':
#             ima = np.rot90(im)
#             imb = np.rot90(ima)
#             imc = np.rot90(imb)
#             imd = np.fliplr(im)
#             ime = np.flipud(im)
#
#         im = np.reshape(im, [3, im.shape[0], im.shape[1]])
#         if mode == 'tr':
#             ima = np.reshape(ima, [3, ima.shape[0], ima.shape[1]])
#             imb = np.reshape(imb, [3, imb.shape[0], imb.shape[1]])
#             imc = np.reshape(imc, [3, imc.shape[0], imc.shape[1]])
#             imd = np.reshape(imd, [3, imd.shape[0], imd.shape[1]])
#             ime = np.reshape(ime, [3, ime.shape[0], ime.shape[1]])
#
#         imlist.append(im)
#         if mode == 'tr':
#             imlist.append(ima)
#             imlist.append(imb)
#             imlist.append(imc)
#             imlist.append(imd)
#             imlist.append(ime)
#
#         lname = row['Label']
#         la = imread(lname)
#         if mode == 'tr':
#             laa = np.rot90(la)
#             lab = np.rot90(laa)
#             lac = np.rot90(lab)
#             lad = np.fliplr(la)
#             lae = np.flipud(la)
#
#         la = np.reshape(la, [1, la.shape[0], la.shape[1]])
#         if mode == 'tr':
#             laa = np.reshape(laa, [1, laa.shape[0], laa.shape[1]])
#             lab = np.reshape(lab, [1, lab.shape[0], lab.shape[1]])
#             lac = np.reshape(lac, [1, lac.shape[0], lac.shape[1]])
#             lad = np.reshape(lad, [1, lad.shape[0], lad.shape[1]])
#             lae = np.reshape(lae, [1, lae.shape[0], lae.shape[1]])
#
#         labellist.append(la)
#         if mode == 'tr':
#             labellist.append(laa)
#             labellist.append(lab)
#             labellist.append(lac)
#             labellist.append(lad)
#             labellist.append(lae)
#
#     imlist = np.array(imlist)
#     labellist = np.array(labellist)
#     return imlist, labellist


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


# Initial weights
def init_weights(module):
    for name, param in module.named_parameters():
        if name.find('weight') != -1:
            if len(param.size()) == 1:
                Cuda(init.uniform(param.data, 1).type(torch.DoubleTensor))
            else:
                Cuda(init.xavier_uniform(param.data).type(torch.DoubleTensor))
        elif name.find('bias') != -1:
            Cuda(init.constant(param.data, 0).type(torch.DoubleTensor))


def Cuda(obj):
    if USE_CUDA:
        if isinstance(obj, tuple):
            return tuple(cuda(o) for o in obj)
        elif isinstance(obj, list):
            return list(cuda(o) for o in obj)
        elif hasattr(obj, 'cuda'):
            return obj.cuda()
    return obj




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


def rle_encoding(x):
    dots = np.where(x.T.flatten() == 1)[0]
    run_lengths = []
    prev = -2
    for b in dots:
        if (b > prev + 1): run_lengths.extend((b + 1, 0))
        run_lengths[-1] += 1
        prev = b
    return run_lengths


def prob_to_rles(x, cutoff=0.5):
    lab_img = label(x > cutoff)
    for i in range(1, lab_img.max() + 1):
        yield rle_encoding(lab_img == i)


def metric(y_pred, target):
    pred_vec = y_pred.view(-1).data.numpy()
    target_vec = target.view(-1).data.numpy()
    label = target_vec.sum()
    pred = (pred_vec > 0.5).astype(np.uint8)
    tp = (pred * target_vec).sum()
    predicted = pred.sum()
    ppv = (tp + 1) / (predicted + label - tp + 1)
    return ppv


def train(bs, sample, vasample, ep, ilr, lr_dec):
    init_lr = ilr

    model = Cuda(UNet())
    init_weights(model)
    opt = torch.optim.Adam(model.parameters(), lr=init_lr)
    opt.zero_grad()
    rows_trn = len(sample['Label'])
    rows_val = len(vasample['Label'])
    batches_per_epoch = rows_trn // bs
    losslists = []
    vlosslists = []

    for epoch in range(ep):
        lr = init_lr * (0.1 ** (epoch // lr_dec))
        order = np.arange(rows_trn)
        losslist = []
        tr_metric_list = []
        va_metric_list = []
        for itr in range(batches_per_epoch):
            # print(itr)
            rows = order[itr * bs: (itr + 1) * bs]
            if itr + 1 == batches_per_epoch:
                rows = order[itr * bs:]
            # read in a batch
            trim = sample['Image'][rows[0]]
            trla = sample['Label'][rows[0]]
            for iit in range(6):
                trimm = trim[iit:iit + 1, :, :, :]
                trlaa = trla[iit:iit + 1, :, :, :]
                minitrlist, trimmdim = minicut(trimm)
                minilalist, trlaadim = minicut(trlaa)

                for iiit in range(minitrlist.shape[0]):
                    xxx = minitrlist[iiit:iiit + 1, :, :, :]
                    yyy = minilalist[iiit:iiit + 1, :, :, :]
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
                    yyy= Cuda(Variable(torch.from_numpy(yyy/255).type(torch.FloatTensor)))
                    pred_mask = model(x) # .cpu() # .round()
                    loss = loss_fn(pred_mask, yyy)
                    losslist.append(loss.cpu().data.numpy()[0])
                    loss.backward()
                    tr_metric = metric(F.sigmoid(pred_mask.cpu()), yyy.cpu())
                    tr_metric_list.append(tr_metric)


        vlosslist = []
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
                    yyy= Cuda(Variable(torch.from_numpy(yyy/255).type(torch.FloatTensor)))
                    pred_maskv = model(x) # .cpu() # .round()
                    vloss = loss_fn(pred_maskv, yyy)
                    vlosslist.append(vloss.cpu().data.numpy()[0])
                    vloss.backward()
                    va_metric = metric(F.sigmoid(pred_maskv.cpu()), yyy.cpu())
                    va_metric_list.append(va_metric)


        lossa = np.mean(losslist)
        vlossa = np.mean(vlosslist)
        tr_score = np.mean(tr_metric_list)
        va_score = np.mean(va_metric_list)
        print(
            'Epoch {:>3} |lr {:>1.5f} | Loss {:>1.5f} | VLoss {:>1.5f} | Train Score {:>1.5f} | Val Score {:>1.5f} '.format(
                epoch + 1, lr, lossa, vlossa, tr_score, va_score))
        opt.step()
        opt.zero_grad()
        losslists.append(lossa)
        vlosslists.append(vlossa)

        for param_group in opt.param_groups:
            param_group['lr'] = lr

        if (epoch + 1) % 10 == 0:
            checkpoint = {
                'epoch': epoch + 1,
                'state_dict': model.state_dict(),
                'optimizer': opt.state_dict(),
            }
            torch.save(checkpoint, '../' + output + '/unet-{}'.format(epoch + 1))
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



def test(tesample, model, group):
    test_ids = []
    rles = []
    if not os.path.exists('../' + output + '/' + group):
        os.makedirs('../' + output + '/' + group)
    for itr in range(len(tesample['ID'])):
        # print(itr)
        teim = tesample['Image'][itr]
        teid = tesample['ID'][itr]
        tedim = tesample['Dim'][itr]
        # print('ori:', teim.shape)
        # xt = Cuda(Variable(torch.from_numpy(teim).type(torch.FloatTensor)))
        minitelist, teimmdim = minicut(teim)
        pred_mask_list = []
        full_pred_maskt = np.zeros((1, 1, teimmdim[0], teimmdim[1]))
        for iiit in range(minitelist.shape[0]):
            teimmm = minitelist[iiit:iiit + 1, :, :, :]
            if USE_CUDA:
                xt = Cuda(Variable(torch.from_numpy(teimmm).type(torch.FloatTensor)))
            else:
                xt = Variable(torch.from_numpy(teimmm).type(torch.FloatTensor))
            pred_mask = F.sigmoid(model(xt)).cpu().data.numpy()  # .round()
            pred_mask_list.append(pred_mask)
        num1 = int(teimmdim[0] / 256)
        num2 = int(teimmdim[1] / 256)
        a = 0
        for co in range(num1):
            for ro in range(num2):
                full_pred_maskt[:, :, co * 256:(co + 1) * 256, ro * 256:(ro + 1) * 256] = pred_mask_list[a]
                a += 1
        # pred_mask = pred_mask(pred_mask > 0.5).type(torch.FloatTensor)
        pred_np = full_pred_maskt.round()
        pred_np = back_scale(pred_np, tedim).astype(np.uint8)
        imsave('../' + output + '/' + group + '/' + teid + '_pred.png', pred_np*255)
        rle = list(prob_to_rles(pred_np))
        rles.extend(rle)
        test_ids.extend([teid] * len(rle))
    sub = pd.DataFrame()
    sub['ImageId'] = test_ids
    sub['EncodedPixels'] = pd.Series(rles).apply(lambda x: ' '.join(str(y) for y in x))

    return sub


tr = pd.read_csv('../inputs/stage_1_train/samples.csv', header=0,
                       usecols=['Image', 'Label', 'Width', 'Height', 'ID'])
va = pd.read_csv('../inputs/stage_1_test/vsamples.csv', header=0,
                       usecols=['Image', 'Label', 'Width', 'Height', 'ID'])
# tr = tr.loc[:200,:]
# vasample = vasample.loc[:2,:]
te = pd.read_csv('../inputs/stage_2_test/samples.csv', header=0, usecols=['Image', 'ID', 'Width', 'Height'])

trsample = dataloader(tr, 'train')
vasample = dataloader(va, 'val')
tebsample = dataloader(te, 'test')


model = train(1, trsample, vasample, int(eps), float(LR), int(lr_decay))
tebsub = test(tebsample, model, 'stage_2_test')
tebsub.to_csv('../' + output + '/stage_2_test_sub.csv', index=False)
