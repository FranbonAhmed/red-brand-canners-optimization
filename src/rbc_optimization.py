"""Red Brand Canners optimization models.

Source-derived LP formulations are based on the portfolio author's graduate workshop report.
The fixed-charge MILP is a portfolio extension added after the original assignment.
"""

import gurobipy as gp
from gurobipy import GRB


def build_base_model():
    m = gp.Model("RBC_base")
    x = {n: m.addVar(lb=0, name=n) for n in ["Aw","Bw","Aj","Bj","Ap","Bp"]}

    m.setObjective(
        246.67*(x["Aw"]+x["Bw"])
        + 198*(x["Aj"]+x["Bj"])
        + 222*(x["Ap"]+x["Bp"]),
        GRB.MAXIMIZE,
    )

    m.addConstr(x["Aw"]+x["Bw"] <= 14400, name="dem_whole")
    m.addConstr(x["Aj"]+x["Bj"] <= 1000, name="dem_juice")
    m.addConstr(x["Ap"]+x["Bp"] <= 2000, name="dem_paste")
    m.addConstr(x["Aw"]+x["Aj"]+x["Ap"] <= 600, name="sup_A")
    m.addConstr(x["Bw"]+x["Bj"]+x["Bp"] <= 2400, name="sup_B")
    m.addConstr(x["Aw"] >= 3*x["Bw"], name="qual_whole")
    m.addConstr(x["Bj"] <= 3*x["Aj"], name="qual_juice")
    return m, x


def build_extra_a_model():
    m = gp.Model("RBC_extra_A")
    Aw = m.addVar(lb=0, name="Aw"); Bw = m.addVar(lb=0, name="Bw")
    Aj = m.addVar(lb=0, name="Aj"); Bj = m.addVar(lb=0, name="Bj")
    Ap = m.addVar(lb=0, name="Ap"); Bp = m.addVar(lb=0, name="Bp")
    AAw = m.addVar(lb=0, name="AAw"); AAj = m.addVar(lb=0, name="AAj"); AAp = m.addVar(lb=0, name="AAp")

    m.setObjective(
        246.67*(Aw+Bw+AAw) + 198*(Aj+Bj+AAj) + 222*(Ap+Bp+AAp)
        - 255*(AAw+AAj+AAp), GRB.MAXIMIZE
    )
    m.addConstr(Aw+Bw+AAw <= 14400, name="dem_whole")
    m.addConstr(Aj+Bj+AAj <= 1000, name="dem_juice")
    m.addConstr(Ap+Bp+AAp <= 2000, name="dem_paste")
    m.addConstr(Aw+Aj+Ap <= 600, name="sup_A")
    m.addConstr(Bw+Bj+Bp <= 2400, name="sup_B")
    m.addConstr(AAw+AAj+AAp <= 80, name="extraA_cap")
    m.addConstr(Aw+AAw >= 3*Bw, name="qual_whole")
    m.addConstr(Bj <= 3*(Aj+AAj), name="qual_juice")
    return m


def build_fixed_charge_milp(setup_cost=50000):
    """Portfolio extension: solve the line-opening decision directly as a MILP.

    The original assignment enumerated all seven non-empty line combinations.
    This formulation scales the same logic using binary setup variables.
    """
    m = gp.Model("RBC_fixed_charge_MILP")
    x = {n: m.addVar(lb=0, name=n) for n in ["Aw","Bw","Aj","Bj","Ap","Bp"]}
    y = {p: m.addVar(vtype=GRB.BINARY, name=f"open_{p}") for p in ["whole","juice","paste"]}

    m.setObjective(
        246.67*(x["Aw"]+x["Bw"])
        + 198*(x["Aj"]+x["Bj"])
        + 222*(x["Ap"]+x["Bp"])
        - setup_cost*(y["whole"]+y["juice"]+y["paste"]),
        GRB.MAXIMIZE,
    )

    # Demand / activation links serve as valid product-level upper bounds.
    m.addConstr(x["Aw"]+x["Bw"] <= 14400*y["whole"], name="activate_whole")
    m.addConstr(x["Aj"]+x["Bj"] <= 1000*y["juice"], name="activate_juice")
    m.addConstr(x["Ap"]+x["Bp"] <= 2000*y["paste"], name="activate_paste")

    m.addConstr(x["Aw"]+x["Aj"]+x["Ap"] <= 600, name="sup_A")
    m.addConstr(x["Bw"]+x["Bj"]+x["Bp"] <= 2400, name="sup_B")
    m.addConstr(x["Aw"] >= 3*x["Bw"], name="qual_whole")
    m.addConstr(x["Bj"] <= 3*x["Aj"], name="qual_juice")
    return m, x, y


def solve_given_order(Q_fixed, quality_fraction):
    """Scenario recourse LP from Part 6; Q_fixed is in 1,000-lb units."""
    m = gp.Model("RBC_contract")
    Aw = m.addVar(lb=0); Bw = m.addVar(lb=0)
    Aj = m.addVar(lb=0); Bj = m.addVar(lb=0)
    Ap = m.addVar(lb=0); Bp = m.addVar(lb=0)
    Q = Q_fixed

    m.setObjective(
        246.67*(Aw+Bw) + 198*(Aj+Bj) + 222*(Ap+Bp) - 200*Q,
        GRB.MAXIMIZE,
    )
    m.addConstr(Aj+Bj <= 1000)
    m.addConstr(Ap+Bp <= 2000)
    m.addConstr(Aw+Aj+Ap <= quality_fraction*Q)
    m.addConstr(Bw+Bj+Bp <= (1-quality_fraction)*Q)
    m.addConstr(Aw >= 3*Bw)
    m.addConstr(Bj <= 3*Aj)
    m.optimize()
    return m.ObjVal


if __name__ == "__main__":
    m, x = build_base_model()
    m.optimize()
    print("Base objective:", m.ObjVal)

    milp, x_milp, y_milp = build_fixed_charge_milp()
    milp.optimize()
    print("Fixed-charge MILP objective:", milp.ObjVal)
    print("Open lines:", {k: int(round(v.X)) for k,v in y_milp.items()})
