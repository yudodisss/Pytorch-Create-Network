import torch
import torch.optim as optim
import torch.nn as nn
import torch.utils.data as Data
from torch.autograd import Variable
from torchvision import transforms
import numpy as np
import Data.DataPre as dp
import Data.DataReload as dr
import Network.Network as Network
import os
import argparse
import random
import yaml
import time

parser = argparse.ArgumentParser(description='params about training')
parser.add_argument('--config', default='Config/Config.yaml', type=str)

def train(args,logs_file):
    
    train_transforms = transforms.Compose([
        dp.NumpyToTensor()
    ])
    test_transforms = transforms.Compose([
        dp.NumpyToTensor()
    ])

    mydataset_train = dr.MyDataset(num_class = args.num_class, is_train = True, root_path=args.Dataset_root_path, transform=train_transforms)
    train_loader = Data.DataLoader(
        dataset=mydataset_train,      # 数据集
        batch_size=args.BATCH_SIZE,   # mini batch size
        shuffle=True,                 # 是否打乱数据集
        num_workers=args.num_workers,        
    )

    mydataset_test = dr.MyDataset(num_class = args.num_class, is_train = False, root_path=args.Dataset_root_path, transform=train_transforms)
    test_loader = Data.DataLoader(
        dataset=mydataset_test,      # 数据集
        batch_size=args.BATCH_SIZE, # mini batch size
        shuffle=False,              # 是否打乱数据集
        num_workers=args.num_workers,        
    )

    with open(logs_file, 'a') as f:
        f.write("%20s%20s%20s\n"%('Epoch:','train loss','test accuracy'))

    network = Network.Network(select_net = args.select_net, use_gpu = args.use_gpu)
    net = network.get_net()
    optimizer = optim.Adam(net.parameters(), lr=args.learning_rate) 
    loss_func = nn.CrossEntropyLoss()

    # restore the parameters 
    if args.use_checkpoint:
        try:
            net.load_state_dict(torch.load(args.checkpoint_path+'/'+args.checkpoint_pre))
        except:
            print("**no checkpoint can not be found**\n")

    for epoch in range(args.EPOCH):
        for step,(b_x,b_y) in enumerate(train_loader):
            network.train_or_test(is_train = True)
            if args.use_gpu:
                b_x = b_x.cuda()
                b_y = b_y.cuda()
            output = net(b_x)
            loss = loss_func(output, b_y)   # cross entropy loss
            optimizer.zero_grad()           # clear gradients for this training step
            loss.backward()                 # backpropagation, compute gradients
            optimizer.step()                # apply gradients
            if args.use_gpu:
                loss = loss.cpu()
            if step % args.logs_frequecy == 0:
                network.train_or_test(is_train = False)
                correct = 0.0
                for (t_x,t_y) in test_loader:
                    if args.use_gpu:
                        t_x = t_x.cuda()
                        t_y = t_y.cuda()
                    test_output = net(t_x)
                    pred_y = torch.max(test_output, 1)[1]
                    correct += pred_y.eq(t_y).sum()
                accuracy = correct.float() / len(mydataset_test)
                if args.use_gpu:
                    accuracy = accuracy.cpu()
                if args.print_logs is True:
                    print('Epoch: ', epoch, '| train loss: %.4f' % loss.data.numpy(), '| test accuracy: %.2f' % accuracy.data.numpy())
                with open(logs_file, 'a') as f:
                    logs_content = "%20d%16.4f%18.2f\n"%(epoch,loss.data.numpy(),accuracy.data.numpy())
                    f.write(logs_content)

    # save only the parameters              
    torch.save(net.state_dict(), args.checkpoint_path+'/'+args.checkpoint_save)

def main():
    args = parser.parse_args()
    with open(args.config) as f:
        config = yaml.load(f)
    print("\n**************************")
    for k, v in config['params'].items():
        setattr(args, k, v)
        print('\n[%s]:'%(k), v)
    print("\n**************************\n")

    # create checkpoint folder to save model
    if not os.path.exists(args.checkpoint_path):
        os.makedirs(args.checkpoint_path)

    # create logs folder to save train logs
    if not os.path.exists(args.logs_path):
        os.makedirs(args.logs_path)
    logs_file = args.logs_path+'/' + \
        str(time.localtime(time.time()).tm_year) + \
        str(time.localtime(time.time()).tm_mon)  + \
        str(time.localtime(time.time()).tm_mday) + \
        str(time.localtime(time.time()).tm_hour) + \
        str(time.localtime(time.time()).tm_min)  + \
        str(time.localtime(time.time()).tm_sec)  + \
        '.txt'

    # check gpu is available or not
    if args.use_gpu:
        if not torch.cuda.is_available():
            args.use_gpu = False
            print("**no gpu can be found**")

    train(args,logs_file)

if __name__ == "__main__":
    main()