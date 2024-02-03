#%matplotlib inline
import matplotlib
import matplotlib.pyplot as plt
import numpy as np #numerical python used for working with arrays, mathematical operations
import xarray as xr #package for labeling and adding metadata to multi-dimensional arrays
import sys
sys.path.append("../PyDDM") #must point to the PyDDM folder
import ddm_analysis_and_fitting as ddm


args = sys.argv

current_input_file = args[1]
print(current_input_file)

ddm_calc = ddm.DDM_Analysis(current_input_file)
print("ddm_calc instance")
ddm_calc.calculate_DDM_matrix()
print("calculate_DDM_matrix done")

ddm_fit = ddm.DDM_Fit(ddm_calc.data_yaml)
print("ddm_fit instance")
fit01 = ddm_fit.fit()

## start loop here to find best fitting points
print("ddm.fit_report")
ddm.fit_report(fit01, q_indices=[3,6,9,22], forced_qs=[3,6], use_new_tau=True, show=True)

print("saving fit results...")
ddm.save_fit_results_to_excel(fit01)

