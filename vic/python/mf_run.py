#%%
import numpy as np
import netCDF4 as nc
import os
os.chdir('/lustre/nobackup/WUR/ESG/liu297/gitrepo/VIC-WUR-GWM-1910/vic_online/python')
from osgeo import gdal
import flopy
import calendar
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
from netCDF4 import Dataset, date2num
import vic_runner as vr
import support_function as sf
from config_module import config_indus_ubuntu 
from osgeo import gdal
from netCDF4 import Dataset, date2num
from matplotlib import pyplot as plt

#%%
class mfrun:
    def __init__(self, current_date,stress_period,config_instance,layer1_head,layer2_head):
        self.current_date = current_date
        self.stress_period = stress_period
        self.config = config_indus_ubuntu
        self.name = '2Ltrans_off'
        self.rclose = 1000
        self.maxinner = 500
        self.maxouter = 100
        self.outer_dvclose = 50
        self.inner_dvclose = 50
        self.top_layer1 = self.config.cal_toplayer_elevation()
        self.layer1_head = layer1_head
        self.layer2_head = layer2_head
        self.startinghead = self.get_startinghead()

    def set_convergence_criteron(self,rclose,maxinner,maxouter,outer_dvclose,inner_dvclose):
        self.rclose = rclose
        self.maxinner = maxinner
        self.maxouter = maxouter
        self.outer_dvclose = 50
        self.inner_dvclose = 50
        return self.rclose,self.maxinner,self.maxouter        
           
    def online_cp_stress_period_data(self):
        #count how many days in this month
        _, days = calendar.monthrange(self.current_date.year, self.current_date.month)
        nstp, tsmult = 1, 1
        perioddata = [days,nstp,tsmult]
        return perioddata
    def get_startinghead(self):
        startingheadl1 = self.layer1_head
        startingheadl2 = self.layer2_head
        self.startinghead = [startingheadl1,startingheadl2]            
        return self.startinghead
    def run_modflow(self):
        print('it is running')
        perioddata = self.online_cp_stress_period_data()
        botm = self.config.cal_botlayer_elevation()
        khor,kver,stor = self.config.get_npf_param()
        CHDstress_period_data = self.config.get_chd_input()
        RCHstress_period_data = self.config.get_rch_param()
        RIVstress_period_data = self.config.get_riv_param()
        sim = flopy.mf6.MFSimulation(sim_name= self.name, 
                                     version='mf6', 
                                     sim_ws=self.config.paths.mfoutput_dir, 
                                     exe_name = self.config.paths.mf6exe,
                                     memory_print_option= None,
                                     #print_input=True, 
                                     verbosity_level= 1, 
                                     write_headers= True, 
                                     #use_pandas = True,
                                     continue_=False, 
                                     nocheck = True,
                                     #lazy_io = True #TODO: this is only for development phase to speed up testing. false it later
                                     )  
        tdis = flopy.mf6.ModflowTdis(sim,
                                     time_units= "DAYS",
                                     #start_date_time= self.current_date,
                                     nper = 1, 
                                     perioddata= perioddata)               
        ims = flopy.mf6.ModflowIms(sim,
                                   complexity='COMPLEX',
                                   print_option="SUMMARY",
                                   outer_dvclose= self.outer_dvclose,      
                                   inner_dvclose= self.inner_dvclose, 
                                   under_relaxation="simple",
                                   under_relaxation_gamma=0.9,
                                   relaxation_factor=0,
                                   linear_acceleration="bicgstab", 
                                   outer_maximum= self.maxouter,
                                   inner_maximum= self.maxinner,
                                   rcloserecord="{} strict".format(self.rclose))
        gwf = flopy.mf6.ModflowGwf(sim,
                                   modelname = self.name,
                                   model_nam_file= f"{self.name}.nam",
                                   exe_name = self.config.paths.mf6exe,
                                   model_rel_path = '.',
                                   list= None,
                                   print_input = True, #todo false it later
                                   print_flows= True, #todo false it later
                                   save_flows= True)
        dis = flopy.mf6.ModflowGwfdis(gwf,
                                      length_units='METERS',
                                      nogrb=True,
                                      xorigin=0,
                                      yorigin=0,
                                      angrot=0,
                                      nlay=self.config.Nlay,
                                      ncol=self.config.Ncol,
                                      nrow=self.config.Nrow,
                                      top=self.top_layer1,
                                      idomain=[self.config.idomain,self.config.idomain],
                                      delr=self.config.delrow,
                                      delc=self.config.delcol,
                                      botm=botm)
        npf = flopy.mf6.ModflowGwfnpf(gwf,
                                      save_flows = True,
                                      print_flows = True,
                                      save_specific_discharge = True,
                                      save_saturation = True,
                                      perioddata = None,
                                      dev_no_newton = False,
                                      icelltype = 0,
                                      k = khor,
                                      k33 = kver
                                      )
        sto = flopy.mf6.ModflowGwfsto(gwf,
                                      save_flows = None,
                                      storagecoefficient = True,
                                      ss_confined_only = None,
                                      iconvert = 0,
                                      ss = stor,
                                      transient = True)
        chd = flopy.mf6.ModflowGwfchd(gwf,
                                      print_input = False,
                                      print_flows = True,
                                      save_flows = True,
                                      stress_period_data = CHDstress_period_data
                                      )
        ic = flopy.mf6.ModflowGwfic(gwf,
                                    strt = self.startinghead
                                    )
        rch = flopy.mf6.ModflowGwfrch(gwf,
                                      stress_period_data = RCHstress_period_data,
                                      save_flows = True
                                      )
        riv = flopy.mf6.ModflowGwfriv(gwf,
                                      stress_period_data = RIVstress_period_data,
                                      save_flows = True
                                      )
        saverecord = [("HEAD", "ALL"), ("BUDGET", "ALL")]
        printrecord = [("HEAD", "ALL"), ("BUDGET", "ALL")]
        headfile = "{}_{}.hds".format(self.name,self.current_date.strftime("%Y%m%d"))
        head_filerecord = [headfile]
        budgetfile = "{}_{}.cbb".format(self.name,self.current_date.strftime("%Y%m%d"))
        budget_filerecord = [budgetfile]
        ov = flopy.mf6.mfgwfoc.ModflowGwfoc(gwf,
                                            saverecord = saverecord,
                                            head_filerecord = head_filerecord,
                                            budget_filerecord = budget_filerecord
                                            )
        print('finish writing the flopy variables \n')
        print(f"writing the simulation for stress period {self.stress_period}...\n")
        sim.write_simulation()
        print('finish writing the simulation \n')
        print(f"running the simulation for stress period {self.stress_period}...\n")
        success, buff = sim.run_simulation()

        if not success:
            raise Exception(f"MODFLOW 6 did not terminate normally for stressperiod: {self.stress_period}\n")
        else:
            print(f"MODFLOW 6 terminated normally for stressperiod: {self.stress_period}\n")
            print(f"extracting the head and budget files for stress period {self.stress_period}...\n")
            head = flopy.utils.binaryfile.HeadFile(self.config.paths.mfoutput_dir+'/'+headfile)
            self.layer1_head = head.get_data()[0] # top
            self.layer2_head = head.get_data()[1] # bot
        return self.layer1_head,self.layer2_head 
    
   # class mf_waterbalance:
                                      
                                      
                                      
                                      
                                      
                                      
                                      
                                      