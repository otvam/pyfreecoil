"""
Module for adding information to the inductor design:
    - design rule check results (assign)
    - mesher and solver PEEC results (assign)
    - converter operation (compute)
"""

__author__ = "Thomas Guillod"
__copyright__ = "Thomas Guillod - Dartmouth College"
__license__ = "Mozilla Public License Version 2.0"

import numpy as np


def _get_solve_2l_ccm(V_in, V_out, I_dc, f_sw, L_mag):
    """
    Compute the waveforms of the two-level Buck in CCM.
    """

    # get the duty cycles
    duty_1 = V_out/V_in
    duty_2 = 1.0-duty_1

    # peak to peak current
    I_pkpk = (V_out*duty_2)/(f_sw*L_mag)

    # AC RMS current
    I_ac = I_pkpk/(2*np.sqrt(3))

    # switches RMS currents
    I_max = I_dc+(I_pkpk/2)
    I_min = I_dc-(I_pkpk/2)
    I_sw_a = np.sqrt((duty_1/3)*((I_max**2)+(I_min**2)+(I_max*I_min)))
    I_sw_b = np.sqrt((duty_2/3)*((I_max**2)+(I_min**2)+(I_max*I_min)))

    return I_pkpk, I_ac, I_sw_a, I_sw_b


def _get_solve_2l_dcm(V_in, V_out, I_dc, f_sw, L_mag):
    """
    Compute the waveforms of the two-level Buck in DCM.
    """

    # inductor voltage
    V_diff = V_in-V_out

    # peak to peak current
    I_pkpk = np.sqrt((2*I_dc)/(L_mag*f_sw*(1/V_diff+1/V_out)))

    # get the duty cycles
    duty_1 = (I_pkpk*L_mag*f_sw)/V_diff
    duty_2 = (I_pkpk*L_mag*f_sw)/V_out

    # total RMS current
    I_rms = np.sqrt(((duty_1+duty_2)/3)*(I_pkpk**2))
    I_ac = np.sqrt(I_rms**2-I_dc**2)

    # switches RMS currents
    I_sw_a = np.sqrt((duty_1/3)*(I_pkpk**2))
    I_sw_b = np.sqrt((duty_2/3)*(I_pkpk**2))

    return I_pkpk, I_ac, I_sw_a, I_sw_b


def _get_solve_3l_ccm(V_in, V_out, I_dc, f_sw, L_mag):
    """
    Compute the waveforms of the three-level Buck in CCM.
    """

    # get the duty cycles
    duty_1 = V_out/V_in
    duty_2 = 0.5-duty_1

    # peak to peak current
    I_pkpk = (V_out*duty_2)/(f_sw*L_mag)

    # AC RMS current
    I_ac = I_pkpk/(2*np.sqrt(3))

    # switches RMS currents
    I_max = I_dc+(I_pkpk/2)
    I_min = I_dc-(I_pkpk/2)
    I_sw_a = np.sqrt((duty_1/3)*((I_max**2)+(I_min**2)+(I_max*I_min)))
    I_sw_b = np.sqrt(((duty_1+2*duty_2)/3)*((I_max**2)+(I_min**2)+(I_max*I_min)))

    return I_pkpk, I_ac, I_sw_a, I_sw_b


def _get_solve_3l_dcm(V_in, V_out, I_dc, f_sw, L_mag):
    """
    Compute the waveforms of the three-level Buck in DCM.
    """

    # inductor voltage
    V_diff = V_in/2-V_out

    # peak to peak current
    I_pkpk = np.sqrt(I_dc/(L_mag*f_sw*(1/V_diff+1/V_out)))

    # get the duty cycles
    duty_1 = (I_pkpk*L_mag*f_sw)/V_diff
    duty_2 = (I_pkpk*L_mag*f_sw)/V_out

    # total RMS current
    I_rms = np.sqrt(((2*duty_1+2*duty_2)/3)*(I_pkpk**2))
    I_ac = np.sqrt(I_rms**2-I_dc**2)

    # switches RMS currents
    I_sw_a = np.sqrt((duty_1/3)*(I_pkpk**2))
    I_sw_b = np.sqrt(((duty_1+2*duty_2)/3)*(I_pkpk**2))

    return I_pkpk, I_ac, I_sw_a, I_sw_b


def _get_modulation(operation, L_mag, topology):
    """
    Compute the converter operation (modulation scheme, waveforms, and losses).
    Support different topologies (two-level Buck and three-level Buck).
    The semiconductor losses are computed with an optimal chip area.
    """

    # extract
    V_in = operation["V_in"]
    V_out = operation["V_out"]
    P_out = operation["P_out"]
    f_mag = operation["f_mag"]

    # extract
    multi_level = topology["multi_level"]
    force_ccm = topology["force_ccm"]
    n_stack_2l = topology["n_stack_2l"]
    n_stack_3l = topology["n_stack_3l"]
    R_on_sp = topology["R_on_sp"]
    E_gg_sp = topology["E_gg_sp"]
    alpha_R_sp = topology["alpha_R_sp"]
    alpha_E_sp = topology["alpha_E_sp"]

    # check that the modulation is feasible
    if (V_out/V_in) > 0.5:
        raise ValueError("invalid modulation index")

    # get the output current
    I_dc = P_out/V_out

    # get modulation and waveforms
    if multi_level:
        # get base parameters
        f_sw = 0.5*f_mag

        # check conduction mode
        I_pkpk = V_out*(0.5-(V_out/V_in))/(f_sw*L_mag)
        run_ccm = I_pkpk < (2.0*I_dc)

        # get conduction mode
        ccm_mode = force_ccm or run_ccm

        # get modulation for the three-level Buck (CCM and DCM)
        if ccm_mode:
            (I_pkpk, I_ac, I_sw_a, I_sw_b) = _get_solve_3l_ccm(V_in, V_out, I_dc, f_sw, L_mag)
        else:
            (I_pkpk, I_ac, I_sw_a, I_sw_b) = _get_solve_3l_dcm(V_in, V_out, I_dc, f_sw, L_mag)

        # number of switches for the topology (without symmetrical switched)
        n_switch = 2.0

        # number of stacked transistors per switch
        n_stack = n_stack_3l
    else:
        # get switching frequency
        f_sw = 1.0*f_mag

        # check conduction mode
        I_pkpk = V_out*(1.0-(V_out/V_in))/(f_mag*L_mag)
        run_ccm = I_pkpk < (2.0*I_dc)

        # get conduction mode
        ccm_mode = force_ccm or run_ccm

        # get modulation for the two-level Buck (CCM and DCM)
        if ccm_mode:
            (I_pkpk, I_ac, I_sw_a, I_sw_b) = _get_solve_2l_ccm(V_in, V_out, I_dc, f_sw, L_mag)
        else:
            (I_pkpk, I_ac, I_sw_a, I_sw_b) = _get_solve_2l_dcm(V_in, V_out, I_dc, f_sw, L_mag)

        # number of switches for the topology (without symmetrical switched)
        n_switch = 1.0

        # number of stacked transistors per switch
        n_stack = n_stack_2l

    # scale the switch parameters for the  stacked transistors
    R_on_sp = R_on_sp*(n_stack**alpha_R_sp)
    E_gg_sp = E_gg_sp*(n_stack**alpha_E_sp)

    # total current through the switches
    I_sw = n_switch*I_sw_a+n_switch*I_sw_b

    # switching losses (with an optimal chip area)
    P_sw = 2.0*I_sw*np.sqrt(f_sw*R_on_sp*E_gg_sp)
    A_sw = I_sw*np.sqrt(R_on_sp/(f_sw*E_gg_sp))

    return I_pkpk, I_dc, I_ac, P_out, P_sw, A_sw


def _get_external(I_tot, external):
    """
    Compute additional loses (external series resistance and loss offset).
    """

    # extract
    R_ext = external["R_ext"]
    P_cst = external["P_cst"]

    # power loss
    P_ext = R_ext*(I_tot**2)

    # total losses
    P_add = P_ext+P_cst

    return P_add


def _get_frequency(f_vec, frequency):
    """
    Match the frequencies from the field simulation with the converter operation.
    """

    # extract
    f_dc = frequency["f_dc"]
    f_ac = frequency["f_ac"]

    # find the closest frequency
    idx_dc = np.argmin(np.abs(f_vec-f_dc))
    idx_ac = np.argmin(np.abs(f_vec-f_ac))

    return idx_dc, idx_ac


def _get_penalty(J_tot, H_dc, H_ac, A_sw, ripple_pkpk, scale):
    """
    Assemble a penalty vector for enforcing design limits:
        - maximum current density in the winding
        - maximum magnetic near-field
        - maximum chip area and ripple

    This vector is used to compute the objective function.
    Positive values indicate limit violations.
    Negative values respect the limits.
    """

    # extract
    H_dc_max = scale["H_dc_max"]
    H_ac_max = scale["H_ac_max"]
    A_sw_max = scale["A_sw_max"]
    J_tot_max = scale["J_tot_max"]
    ripple_pkpk_max = scale["ripple_pkpk_max"]

    # scale penalties
    penalty_vec = np.array([
        J_tot/J_tot_max-1.0,
        H_dc/H_dc_max-1.0,
        H_ac/H_ac_max-1.0,
        A_sw/A_sw_max-1.0,
        ripple_pkpk/ripple_pkpk_max-1.0,
    ], dtype=np.float64)

    # clip the value
    penalty_vec = np.clip(penalty_vec, -1.0, +1.0)

    return penalty_vec


def _get_loss(P_dc, P_ac, P_add, P_sw, P_out):
    """
    Assemble a vector containing the different loss components.
    This vector is used to compute the objective function.
    """

    # converter losses
    loss_vec = np.array([
        P_dc,
        P_ac,
        P_add,
        P_sw,
    ], dtype=np.float64)

    # scale losses
    loss_vec = loss_vec/P_out

    return loss_vec


def add_data_valid(design, data_valid):
    """
    Assign the design rule check results to the design.
    Positive values indicate design rule violations.
    Negative values respect the rule rules.
    """

    # extract
    valid_boundary = data_valid["valid_boundary"]
    valid_clearance = data_valid["valid_clearance"]
    valid_length = data_valid["valid_length"]
    valid_distance = data_valid["valid_distance"]
    valid_width = data_valid["valid_width"]
    valid_angle = data_valid["valid_angle"]
    valid_diff = data_valid["valid_diff"]
    valid_radius = data_valid["valid_radius"]

    # get the score
    validity_vec = np.array([
        valid_boundary,
        valid_clearance,
        valid_length,
        valid_distance,
        valid_width,
        valid_angle,
        valid_diff,
        valid_radius,
    ], dtype=np.float64)

    # assign status
    design["checked"] = True

    # assign data
    design["valid_boundary"] = valid_boundary
    design["valid_clearance"] = valid_clearance
    design["valid_length"] = valid_length
    design["valid_width"] = valid_width
    design["valid_distance"] = valid_distance
    design["valid_angle"] = valid_angle
    design["valid_diff"] = valid_diff
    design["valid_radius"] = valid_radius

    # assign data
    design["validity_vec"] = validity_vec

    return design


def add_data_peec(design, data_peec):
    """
    Assign the mesher and solver results to the design.
    """

    # extract
    f_vec = data_peec["f_vec"]
    R_vec = data_peec["R_vec"]
    L_vec = data_peec["L_vec"]
    H_vec = data_peec["H_vec"]
    J_vec = data_peec["J_vec"]

    # assign status
    design["solved"] = True

    # assign data
    design["f_vec"] = f_vec
    design["R_vec"] = R_vec
    design["L_vec"] = L_vec
    design["H_vec"] = H_vec
    design["J_vec"] = J_vec

    return design


def add_data_converter(design, data_converter):
    """
    Compute and assign the converter operation to the design.
    The computed values are used for the objective function.
    """

    # extract
    frequency = data_converter["frequency"]
    operation = data_converter["operation"]
    external = data_converter["external"]
    topology = data_converter["topology"]
    scale = data_converter["scale"]

    # extract
    checked = design["checked"]
    solved = design["solved"]
    f_vec = design["f_vec"]
    R_vec = design["R_vec"]
    L_vec = design["L_vec"]
    H_vec = design["H_vec"]
    J_vec = design["J_vec"]

    # check if the converter operation can be computed
    if (not checked) or (not solved):
        return design

    # get frequency indices
    [idx_dc, idx_ac] = _get_frequency(f_vec, frequency)

    # get equivalent circuit
    L_mag = L_vec[idx_ac]
    R_dc = R_vec[idx_dc]
    R_ac = R_vec[idx_ac]

    # solve the converter modulation
    (I_pkpk, I_dc, I_ac, P_out, P_sw, A_sw) = _get_modulation(operation, L_mag, topology)

    # inductor power losses
    P_dc = R_dc*(I_dc**2)
    P_ac = R_ac*(I_ac**2)

    # total current
    I_tot = np.sqrt((I_dc**2)+(I_ac**2))

    # additional losses
    P_add = _get_external(I_tot, external)

    # total losses
    P_mag = P_dc+P_ac
    P_tot = P_mag+P_add+P_sw

    # converter figures of merit
    eta_mag = P_out/(P_out+P_mag)
    eta_tot = P_out/(P_out+P_tot)
    ripple_pkpk = I_pkpk/I_dc

    # scale fields with respect to the RMS currents
    (H_dc, H_ac) = (H_vec[idx_dc]*I_dc, H_vec[idx_ac]*I_ac)
    (J_dc, J_ac) = (J_vec[idx_dc]*I_dc, J_vec[idx_ac]*I_ac)

    # total current density
    J_tot = np.hypot(J_dc, J_ac)

    # get penalty and loss vector (for the objective function)
    penalty_vec = _get_penalty(J_tot, H_dc, H_ac, A_sw, ripple_pkpk, scale)
    loss_vec = _get_loss(P_dc, P_ac, P_add, P_sw, P_out)

    # assign status
    design["scored"] = True

    # assign data
    design["P_sw"] = P_sw
    design["P_add"] = P_add
    design["P_mag"] = P_mag
    design["P_tot"] = P_tot
    design["eta_mag"] = eta_mag
    design["eta_tot"] = eta_tot
    design["A_sw"] = A_sw
    design["J_tot"] = J_tot
    design["I_tot"] = I_tot
    design["I_pkpk"] = I_pkpk
    design["ripple_pkpk"] = ripple_pkpk
    (design["P_dc"], design["P_ac"]) = (P_dc, P_ac)
    (design["I_dc"], design["I_ac"]) = (I_dc, I_ac)
    (design["J_dc"], design["J_ac"]) = (J_dc, J_ac)
    (design["H_dc"], design["H_ac"]) = (H_dc, H_ac)

    # assign data
    design["penalty_vec"] = penalty_vec
    design["loss_vec"] = loss_vec

    return design
