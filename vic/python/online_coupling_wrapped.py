#%%
import os 
import sys
sys.path.append('/lustre/nobackup/WUR/ESG/liu297/gitrepo/VIC-WUR-GWM-1910/vic_online/python')
import flopy
import numpy as np
import xarray as xr
import netCDF4 as nc
import subprocess  # for calling shell commands
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import vic_runner as vr
import support_function as sf
from config_module import config_indus_ubuntu
from osgeo import gdal
from netCDF4 import Dataset, date2num
from matplotlib import pyplot as plt
import mf_run as mf

%env LD_LIBRARY_PATH=/shared/legacyapps/netcdf/gcc/64/4.6.1/lib:$LD_LIBRARY_PATH   

cwd = '/lustre/nobackup/WUR/ESG/liu297/gitrepo/VIC-WUR-GWM-1910/vic_online/'
config_indus_ubuntu.paths.set_template_dir(os.path.join(cwd, 'python', 'VIC_config_file_naturalized_template_pyread_anunna.txt'))
config_indus_ubuntu.paths.set_statefile_dir(os.path.join(cwd, 'python', 'statefile'))
config_indus_ubuntu.paths.set_configfile_dir(os.path.join(cwd, 'python', 'configfile'))
config_indus_ubuntu.paths.set_vic_executable('/lustre/nobackup/WUR/ESG/liu297/vic_indus/11indus_run/99vic_offline_src/drivers/image/vic_image_gwm.exe')
config_indus_ubuntu.set_startstamp(datetime(1968, 1, 1))
config_indus_ubuntu.paths.set_mfinput_dir('/lustre/nobackup/WUR/ESG/yuan018/04Input_Indus/')
config_indus_ubuntu.paths.set_mfoutput_dir('/lustre/nobackup/WUR/ESG/liu297/gitrepo/VIC-WUR-GWM-1910/vic_online/python/mfoutput/workspace/')
config_indus_ubuntu.set_humanimpact(False)



current_date = datetime(1968,1,1)
finishdate = datetime(1968, 4, 1)

# Loop over the dates
while current_date <= finishdate:
    print("Running VIC for the time step [{}-{}]".format(current_date.year, current_date.month))
    #generate dmy for VIC run
    startyear, startmonth, startday = sf.startdate(current_date)
    endyear, endmonth, endday = sf.enddate(current_date)
    stateyear, statemonth, stateday = sf.statefiledate(current_date)
    init_date,init_datestr = sf.init_datestr(current_date)
    
         
    # prepare VIC config file
    config_file = vr.prepare_vic(startyear, startmonth, startday, 
               endyear, endmonth, endday, 
               stateyear, statemonth, stateday, 
               init_date, init_datestr, 
               config_indus_ubuntu)    
    vr.run_vic(config_indus_ubuntu, config_file, startyear, startmonth)    
        
    ts_gwrecharge, ts_discharge, ts_gwabstract = vr.PostProcessVIC(config_indus_ubuntu, startyear, startmonth) # read VIC output and prepare for MODFLOW input
    
    
    config_indus_ubuntu.paths.set_ts_gwrecharge(ts_gwrecharge)
    config_indus_ubuntu.paths.set_ts_discharge(ts_discharge)
    config_indus_ubuntu.paths.set_vic_output_file(os.path.join(config_indus_ubuntu.paths.output_dir + 'fluxes_naturalized_gwm_.{current_date.year}_{current_date.month}.nc'))
        
    stress_period = config_indus_ubuntu.timestep_counter() # let stress period ++1 after each VIC run
    print(f"start assigning the MODFLOW inputs for stress period {stress_period}...\n")

    if stress_period == 0:
        layer1_head = config_indus_ubuntu.get_initial_head()[0]
        layer2_head = config_indus_ubuntu.get_initial_head()[1]
    
    mfrun = mf.mfrun(current_date,stress_period,config_indus_ubuntu,layer1_head,layer2_head) # 把日期传递给mfrun这个类
   
    layer1_head, layer2_head = mfrun.run_modflow() # run MODFLOW and get the head for each layer
    
    

    
    
    
    
    #mf.PostProcessMF() 
        #1. prepare GWD data to identfy conditon of GWD and VIC soil layer depth
        
        #2. export Baseflow data from Water Budget output, save it as a netcdf file for VIC to read in the next time step
    
    #mf.Feedback2VIC()
        #1. read the current soil moisture and update it based on the condition. 
    
    #vr.update_statefile()
        #1. update the statefile's soil moisture for the next time step. 
    
    #move to next time step
    current_date += relativedelta(months=1)
# %%
