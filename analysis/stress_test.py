#!/usr/bin/env python3
"""Revised counterfactual credit-loss engine. All monetary arrays are USD per
initial USD principal. No simulated quantity is represented as observed data.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import pandas as pd

SEED=20260928
HORIZON=12
MAX_DELAY=2
N_PATHS=20000
BASE_BLOCK=3
THRESHOLD=1.5
RATE_RULES=('static_20','adaptive_75','indexed_100','smooth_12','partial_adjust','lower_cap')
@dataclass(frozen=True)
class Mechanism:
    name: str='timely'
    delay: int=0
    haircut: float=.08
    congestion: float=.20
    penalty: float=.13
    haircut_cap: float=.30
MECHANISMS=(Mechanism(),Mechanism('delay_only',1),Mechanism('haircut_only',0,.15),Mechanism('delayed_stress',1,.15))

def collateral_distribution(name='base'):
    if name=='buffered':
        grid=np.linspace(2,3,31); w=np.ones(31)
    else:
        grid=np.linspace(1.5,2.25,31)
        if name=='base':
            w=np.where(grid<=1.75,(grid-1.5)/.25,(2.25-grid)/.5)
            w[[0,-1]]=1e-6
        elif name=='uniform': w=np.ones(31)
        elif name=='near_threshold': w=np.exp(-8*(grid-1.5))
        else: raise ValueError(name)
    return grid,w/w.sum()

def moving_block_bootstrap(data,n_paths,horizon,block,rng,dates=None):
    """Non-circular full blocks; never bridge deleted calendar observations.
    Independent starts sampled uniformly with replacement; truncate last block.
    """
    data=np.asarray(data,float)
    starts=np.arange(len(data)-block+1)
    if dates is not None:
        ordinal=pd.PeriodIndex(dates,freq='M').asi8
        starts=np.array([s for s in starts if np.all(np.diff(ordinal[s:s+block])==1)])
    if not len(starts): raise ValueError('No contiguous full blocks')
    selected=rng.choice(starts,size=(n_paths,math.ceil(horizon/block)))
    idx=(selected[:,:,None]+np.arange(block)).reshape(n_paths,-1)[:,:horizon]
    return data[idx]

def annual_rate_path(fx,rule):
    n,t=fx.shape
    if rule not in RATE_RULES:raise ValueError(rule)
    a=np.full((n,t),.20)
    for m in range(1,t):
        k=12 if rule=='smooth_12' else 3
        hist=fx[:,max(0,m-k):m]
        # No unobserved pre-history is imputed. Expanding lag until k exists.
        annual=np.maximum(np.expm1(np.log1p(hist).mean(axis=1)*12),0)
        target=np.clip((.05+annual) if rule=='indexed_100' else (.10+.75*annual),.05,
                       2 if rule=='indexed_100' else (.60 if rule in ('smooth_12','partial_adjust','lower_cap') else 1.5))
        if rule=='static_20':continue
        if rule=='partial_adjust':target=a[:,m-1]+np.clip(.25*(target-a[:,m-1]),-.05,.05)
        a[:,m]=target
    return a

def simulate_portfolio(paths,rule='adaptive_75',mechanism=Mechanism(),distribution='base',weights=None,grid=None):
    n,t,_=paths.shape
    if t<HORIZON+mechanism.delay:raise ValueError('Need full close-out extension')
    if grid is None:grid,base_weights=collateral_distribution(distribution)
    else:base_weights=np.ones(len(grid))/len(grid)
    w=base_weights if weights is None else np.asarray(weights,float)
    if np.any(w<0) or not np.isclose(w.sum(),1):raise ValueError('Invalid exposure weights')
    fx=np.cumprod(1+paths[:,:,0],axis=1)
    crypto=np.cumprod(1+paths[:,:,1],axis=1)
    rates=annual_rate_path(paths[:,:,0],rule)
    U=np.cumprod(1+rates/12,axis=1)
    D=U/fx
    C=grid[None,:,None]*crypto[:,None,:]
    ratio=C/D[:,None,:]
    breach=ratio[:,:,:HORIZON]<THRESHOLD
    has=breach.any(axis=2)
    first=np.where(has,breach.argmax(axis=2),-1)
    execute=np.where(has,first+mechanism.delay,-1)
    # First breach is irrevocable; no new positions/breaches after month 12.
    settled=np.where(has,execute,HORIZON-1)
    execution_share=np.stack([((execute==m)*w).sum(axis=1) for m in range(t)],axis=1)
    row=np.arange(n)[:,None]
    debt=D[row,settled]
    coll=np.take_along_axis(C,settled[:,:,None],axis=2)[:,:,0]
    fx_set=fx[row,settled]
    haircut=np.minimum(mechanism.haircut_cap,mechanism.haircut+mechanism.congestion*execution_share[row,settled])
    haircut=np.where(has,haircut,0)
    proceeds=coll*(1-haircut)
    recovery=np.where(has,np.minimum(debt,proceeds),debt)
    bad=debt-recovery
    penalty=np.where(has,np.minimum(mechanism.penalty*debt,np.maximum(proceeds-debt,0)),0)
    returned=np.where(has,np.maximum(proceeds-debt-penalty,0),coll)
    # Financing-side effect includes the auction haircut and collectible penalty,
    # but excludes pre-sale collateral investment returns and post-closeout returns.
    financing=1-(recovery+penalty+haircut*coll)
    gross=(bad*w).sum(axis=1)
    liq=(has*w).sum(axis=1)
    pending=has & (execute>=HORIZON)
    executed12=has & (execute<HORIZON)
    terminal_under=pending & (ratio[:,:,HORIZON-1]<1)
    # Matched non-interest-bearing LCU funding, retired at loan settlement.
    # This is an accounting diagnostic, not a peg or liquidity/run simulation.
    margin=(recovery+penalty-1/fx_set)*w
    ledger=np.stack([.10+(margin*(settled<=m)).sum(axis=1) for m in range(t)],axis=1)
    safe=lambda z,d:float(z/d) if d>0 else float('nan')
    surv=~has
    loss_liq_denom=float((debt*has*w).sum())
    se=gross.std(ddof=1)/np.sqrt(n) if n>1 else 0
    cvar=float(np.sort(gross)[-max(1,math.ceil(.01*n)):].mean())
    out=dict(rate_rule=rule,mechanism=mechanism.name,distribution=distribution,paths=n,
        probability_any_liquidation=float(has.any(axis=1).mean()),
        expected_liquidated_exposure_share=float(liq.mean()),
        position_liquidation_probability=float(liq.mean()),
        breach_exposure_share=float(liq.mean()),
        executed_by_month12_share=float((executed12*w).sum(axis=1).mean()),
        pending_at_month12_share=float((pending*w).sum(axis=1).mean()),
        terminal_undercollateralized_share=float((terminal_under*w).sum(axis=1).mean()),
        terminal_undercollateralized_debt_ratio=float((D[:,HORIZON-1,None]*terminal_under*w).sum(axis=1).mean()),
        mean_bad_debt_ratio=float(gross.mean()),bad_debt_cvar_99=cvar,
        bad_debt_var_99=float(np.quantile(gross,.99)),mc_se_bad_debt=float(se),
        bad_debt_per_liquidated_debt=safe(gross.sum(),loss_liq_denom),
        financing_effect_all=float((financing*w).sum(axis=1).mean()),
        financing_effect_survivors=safe((financing*surv*w).sum(),(surv*w).sum()),
        financing_effect_liquidated=safe((financing*has*w).sum(),(has*w).sum()),
        survivor_exposure_share=float((surv*w).sum(axis=1).mean()),
        mean_penalty_ratio=float((penalty*w).sum(axis=1).mean()),
        reserve_breach_10pct=float((gross>.10).mean()),
        accounting_capital_deficit_probability=float((ledger.min(axis=1)<0).mean()),
        mean_final_accounting_equity_ratio=float(ledger[:,-1].mean()))
    cohort=pd.DataFrame({'initial_collateral_ratio':grid,'exposure_weight':w,'liquidation_probability':has.mean(axis=0),'mean_bad_debt_ratio':bad.mean(axis=0)})
    arrays=dict(loss=gross,liquidated=liq,cohort_bad=bad,cohort_financing=financing,has=has,
                executed12=executed12,pending=pending,debt=debt,collateral=coll,recovery=recovery,
                penalty=penalty,returned=returned,haircut=haircut,ledger=ledger,
                rates=rates,financing=financing,weights=w,fx=fx,settled=settled)
    return out,cohort,arrays

def rate_diagnostics(paths,rule,currency):
    _,_,arr=simulate_portfolio(paths,rule)
    a=arr['rates'][:,:HORIZON]
    active=(arr['settled'][:,:,None]>=np.arange(HORIZON)[None,None,:])
    wt=(active*arr['weights'][None,:,None]).sum(axis=1)
    cap={'static_20':None,'adaptive_75':1.5,'indexed_100':2.,'smooth_12':.6,'partial_adjust':.6,'lower_cap':.6}[rule]
    def quantile(values,weights,q):
        v=values.ravel();w=weights.ravel();valid=w>0;v=v[valid];w=w[valid]
        order=np.argsort(v,kind='stable');return float(v[order][np.searchsorted(np.cumsum(w[order]),q*w.sum())])
    changes=np.abs(np.diff(a));change_weights=wt[:,1:]
    return dict(currency=currency,rate_rule=rule,mechanism='timely',collateral='ETH',
        weighting='initial-principal months while debt remains outstanding',
        mean=float(np.average(a,weights=wt)),median=quantile(a,wt,.5),p90=quantile(a,wt,.9),p99=quantile(a,wt,.99),maximum=float(a[wt>0].max()),
        cap_frequency=0 if cap is None else float(np.average(np.isclose(a,cap),weights=wt)),
        mean_abs_monthly_change=float(np.average(changes,weights=change_weights)),
        median_abs_monthly_change=quantile(changes,change_weights,.5),
        posted_mean=float(a.mean()),posted_median=float(np.median(a)))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--paths',type=int,default=N_PATHS)
    parser.add_argument('--sensitivity-paths',type=int,default=5000)
    parser.add_argument('--outer-replicates',type=int,default=100)
    args=parser.parse_args()
    results=Path('results');results.mkdir(exist_ok=True)
    panel=pd.read_csv('data/processed/joint_monthly_market_panel.csv',parse_dates=['month']).dropna()
    output={k:[] for k in ['main_results','cohort_results','rate_diagnostics','joint_sensitivity','robustness','historical_replay','principal_ablation','input_uncertainty']}
    grids=('base','uniform','near_threshold','buffered')
    for ci,currency in enumerate(('ARS','TRY')):
      for ai,asset in enumerate(('ETH','BTC')):
        print(currency,asset,flush=True)
        seed=SEED+100*ci+ai
        data=panel[[currency.lower()+'_depreciation',asset.lower()+'_return']].to_numpy()
        dates=panel.month
        paths=moving_block_bootstrap(data,args.paths,HORIZON+MAX_DELAY,3,np.random.default_rng(seed),dates)
        def run(paths,rule='adaptive_75',mech=Mechanism(),dist='base',**extra):
            row,coh,arr=simulate_portfolio(paths,rule,mech,dist)
            row.update(currency=currency,collateral=asset,**extra)
            return row,coh,arr
        for rule in RATE_RULES:
          for mech in MECHANISMS:
            row,coh,arr=run(paths,rule,mech)
            output['main_results'].append(row)
            coh=coh.assign(currency=currency,collateral=asset,rate_rule=rule,mechanism=mech.name)
            output['cohort_results'].extend(coh.to_dict('records'))
          if ai==0:output['rate_diagnostics'].append(rate_diagnostics(paths,rule,currency))
        # Full blocks and 14-month windows keep comparisons on identical samples.
        for start in range(len(data)-(HORIZON+MAX_DELAY)+1):
          for mech in MECHANISMS:
            row,_,_=run(data[start:start+HORIZON+MAX_DELAY][None],mech=mech,window_start=str(dates.iloc[start].date()))
            output['historical_replay'].append(row)
        if ai:continue
        base,coh,arr=run(paths)
        output['robustness'].append(dict(base,variation='block_3'))
        for block in (1,6):
            p=moving_block_bootstrap(data,args.paths,14,block,np.random.default_rng(seed+block),dates)
            r,_,_=run(p,variation=f'block_{block}');output['robustness'].append(r)
        # Calendar-aware deletion avoids stitching December across a missing year.
        masks=[(f'omit_{yr}',dates.dt.year!=yr) for yr in sorted(dates.dt.year.unique())]
        masks += [('early_2020_2021',dates.dt.year<=2021),('late_2022_2023',dates.dt.year>=2022)]
        for label,mask in masks:
            d=data[mask];dt=dates[mask]
            p=moving_block_bootstrap(d,args.paths,14,3,np.random.default_rng(seed),dt)
            r,_,_=run(p,variation=label,calibration_months=len(d));output['robustness'].append(r)
        # Parametric benchmark: iid bivariate Gaussian log returns, estimated moments.
        log=np.log1p(data)
        p=np.expm1(np.random.default_rng(seed).multivariate_normal(log.mean(0),np.cov(log.T),size=(args.paths,14)))
        r,_,_=run(p,variation='iid_gaussian_log_returns');output['robustness'].append(r)
        # Measurement-convention diagnostic from the same archived daily prices.
        mixed=panel.copy()
        daily=pd.read_csv(f'data/raw_prices/coinmetrics_{asset.lower()}.csv',parse_dates=['time'])
        eom=daily.set_index('time').PriceUSD.resample('MS').last().pct_change()
        mixed[asset.lower()+'_return']=mixed.month.map(eom)
        md=mixed[[currency.lower()+'_depreciation',asset.lower()+'_return']].to_numpy()
        p=moving_block_bootstrap(md,args.paths,14,3,np.random.default_rng(seed),dates)
        r,_,_=run(p,variation='legacy_mixed_measurement');output['robustness'].append(r)
        # Principal-by-CR product portfolio. Marginalize only after explicit construction.
        q=pd.read_csv('data/processed/portfolio_principal_quantiles.csv')
        w=arr['weights'];principal=np.array(q.total_principal_usd);principal/=principal.sum()
        for label,pw in [('makerdao_principal',principal),('equal_principal',np.ones(100)/100),('normalized_unit_with_cr_weights',np.ones(1)),('literal_one_dollar_per_cr_point',np.ones(1))]:
            joint=np.outer(pw,np.ones(len(w))/len(w) if label=='literal_one_dollar_per_cr_point' else w)
            collapsed=joint.sum(0)
            a,_,aa=simulate_portfolio(paths,weights=collapsed)
            output['principal_ablation'].append(dict(currency=currency,scheme=label,synthetic_cells=joint.size,
                mean_bad_debt_ratio=a['mean_bad_debt_ratio'],bad_debt_cvar_99=a['bad_debt_cvar_99'],
                expected_liquidated_exposure_share=a['expected_liquidated_exposure_share'],
                maximum_path_loss_difference=float(np.max(np.abs(aa['loss']-arr['loss'])))))
        # Joint parameter grid, identical first N paths across all combinations.
        for dist in grids:
          for haircut in (.05,.08,.15):
            for slope in (0.,.20,.40):
              for delay in (0,1,2):
                mech=Mechanism('joint_grid',delay,haircut,slope)
                r,_,_=run(paths[:args.sensitivity_paths],mech=mech,dist=dist,base_haircut=haircut,congestion_slope=slope,delay_months=delay)
                output['joint_sensitivity'].append(r)
        # Outer block resampling of 42 observations, inner simulation of 2,000 paths.
        # Percentile bands are descriptive input-resampling uncertainty, not coverage claims.
        for b in range(args.outer_replicates):
            outer=moving_block_bootstrap(data,1,len(data),3,np.random.default_rng(seed+10000+b),dates)[0]
            inner=moving_block_bootstrap(outer,2000,14,3,np.random.default_rng(seed+20000+b))
            r,_,_=run(inner,replicate=b);output['input_uncertainty'].append(r)
    for name,rows in output.items():pd.DataFrame(rows).to_csv(results/f'{name}.csv',index=False,float_format='%.12g')
    checksums={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('data').rglob('*')) if p.is_file()}
    metadata=dict(seed=SEED,paths=args.paths,sensitivity_paths=args.sensitivity_paths,outer_replicates=args.outer_replicates,inner_paths=2000,
                  horizon=HORIZON,extension=MAX_DELAY,calibration_return_months=len(panel),input_sha256=checksums,
                  numpy_version=np.__version__,pandas_version=pd.__version__,rate_rules=RATE_RULES,
                  mechanisms=[asdict(m) for m in MECHANISMS])
    (results/'run_metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print('Completed revised simulations',flush=True)
if __name__=='__main__':main()
