'''
predict the coefficients with the trained NN
given the scattered data
'''

import os
import json
import argparse
import numpy as np
import scipy.io
import torch
import torch.utils.data
import network

# TODO: add config for both data and predictor
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_path", default="./data/star3_kh10_n48_100/forward_data.mat", type=str)
    parser.add_argument("--model_path", default="./data/star3_kh10_n48_100/test", type=str)
    parser.add_argument("--print_coef", default=False, type=bool)
    args = parser.parse_args()

    f = open(os.path.join(args.model_path, "data_config.json"))
    data_cfg = json.load(f)
    f.close()
    
    g = open(os.path.join(args.model_path, "train_config.json"))
    train_cfg = json.load(g)
    g.close()
    return args, data_cfg, train_cfg

def main():
    args, data_cfg, train_cfg = parse_args()
    idx = args.model_path.rfind('/')
    model_name = args.model_path[idx+1:]
    
    # load data
    data = scipy.io.loadmat(args.data_path)
    f = open(os.path.join(args.model_path, "std.txt"))
    std = f.read()
    std = float(std)
    
    #load predictor
    if model_name == 'test':
        loaded_net = network.ConvNet(data_cfg, train_cfg)
    elif model_name == 'Fourier':
        loaded_net = network.ComplexNet(data_cfg, train_cfg)
    if torch.cuda.is_available():
        loaded_net.load_state_dict(torch.load(os.path.join(args.model_path, "model.pt")))
    else:
        loaded_net.load_state_dict(torch.load(os.path.join(args.model_path, "model.pt"), map_location=torch.device('cpu')))
    
    # apply the predictor to obtian an initialization
    if model_name == 'test':
        uscat_all = data["uscat_all"].real / std # the scattered data
        uscat_all = torch.from_numpy(uscat_all[:, None, :, :]).float()
        coef_pred = loaded_net(uscat_all)
    elif model_name == 'Fourier':
        uscat_all = data["uscat_all"]
        uscat_ft = np.fft.fft2(uscat_all)
        ft_real = uscat_ft.real
        ft_imag = uscat_ft.imag
        ft_real = torch.from_numpy(ft_real[:, None, :, :] / std).float()
        ft_imag = torch.from_numpy(ft_imag[:, None, :, :] / std).float()
        coef_pred = loaded_net(ft_real, ft_imag)
    
    # save predicted coef
    if args.data_path[-4:] == ".mat":
        new_data_path = args.data_path[:-4]
    else:
        new_data_path = args.data_path

    model_name = os.path.basename(os.path.normpath(args.model_path))

    scipy.io.savemat(
        new_data_path + "_predby_" + model_name + ".mat",
        {"coef_pred": coef_pred.detach().numpy().astype('float64'),
         "coef_val": data["coefs_all"],
         "cfg_str": data["cfg_str"][0]}
    )
    
    # only for inverse code with data_type=nn
    if args.print_coef:
        coef_pred_np = coef_pred.detach().numpy() #shape 1 x (2*nc+1)
        print("start to print the coefficients")
        [print(num) for num in coef_pred_np[0]]

if __name__ == '__main__':
    main()