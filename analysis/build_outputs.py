#!/usr/bin/env python3
"""Generate every displayed result directly from revision CSVs."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('results');T=Path('tables');F=Path('figures')
T.mkdir(exist_ok=True);F.mkdir(exist_ok=True)
labels={'static_20':'Static 20','adaptive_75':'Adaptive 75','indexed_100':'Indexed 100','smooth_12':'Trailing 12','partial_adjust':'Partial adjustment','lower_cap':'Lower cap'}
mechs={'timely':'Timely','delay_only':'Delay only','haircut_only':'Haircut only','delayed_stress':'Delayed stressed'}
def esc(x):return str(x).replace('_',r'\_').replace('%',r'\%')
def table(name,headers,rows,align=None):
    align=align or ('l'+'r'*(len(headers)-1))
    text='\\begin{tabular}{'+align+'}\n\\toprule\n'+' & '.join(headers)+r' \\'+'\n\\midrule\n'
    text+='\n'.join(' & '.join(map(str,row))+r' \\' for row in rows)
    text+='\n\\bottomrule\n\\end{tabular}\n'
    (T/(name+'.tex')).write_text(text)
def pct(x):return f'{100*x:.2f}'
m=pd.read_csv(R/'main_results.csv');base=m.query("collateral=='ETH' and mechanism=='timely'")
table('main',['Currency','Rule','Liq.','Loss','CVaR$_{99}$','Net effect'],[[r.currency,labels[r.rate_rule],pct(r.expected_liquidated_exposure_share),pct(r.mean_bad_debt_ratio),pct(r.bad_debt_cvar_99),pct(r.financing_effect_all)] for r in base.itertuples()], 'llrrrr')
btc=m.query("collateral=='BTC' and mechanism=='timely'")
table('btc',['Currency','Rule','Liq.','Loss','CVaR$_{99}$','Net effect'],[[r.currency,labels[r.rate_rule],pct(r.expected_liquidated_exposure_share),pct(r.mean_bad_debt_ratio),pct(r.bad_debt_cvar_99),pct(r.financing_effect_all)] for r in btc.itertuples()], 'llrrrr')
mech=m.query("collateral=='ETH' and rate_rule=='adaptive_75'")
table('mechanisms',['Currency','Auction','Breach','Executed','Pending','Loss','CVaR$_{99}$'],[[r.currency,mechs[r.mechanism],pct(r.breach_exposure_share),pct(r.executed_by_month12_share),pct(r.pending_at_month12_share),pct(r.mean_bad_debt_ratio),pct(r.bad_debt_cvar_99)] for r in mech.itertuples()], 'llrrrrr')
table('capital',['Currency','Auction','Any liq.','Under-coll.','Credit budget','Capital gap'],[[r.currency,mechs[r.mechanism],pct(r.probability_any_liquidation),pct(r.terminal_undercollateralized_share),pct(r.reserve_breach_10pct),pct(r.accounting_capital_deficit_probability)] for r in mech.itertuples()], 'llrrrr')
table('borrower',['Currency','Rule','Survivors','Liquidated','All','Loss/liq. debt'],[[r.currency,labels[r.rate_rule],pct(r.financing_effect_survivors),pct(r.financing_effect_liquidated),pct(r.financing_effect_all),pct(r.bad_debt_per_liquidated_debt)] for r in base.itertuples()], 'llrrrr')
rates=pd.read_csv(R/'rate_diagnostics.csv')
for c in ['ARS','TRY']:
    table('rates_'+c,['Rule','Mean','Median','P90','P99','Max','At cap','Change'],[[labels[r.rate_rule]]+[pct(getattr(r,k)) for k in ['mean','median','p90','p99','maximum','cap_frequency','mean_abs_monthly_change']] for r in rates.query('currency==@c').itertuples()], 'lrrrrrrr')
rob=pd.read_csv(R/'robustness.csv')
rl={'block_3':'Base: block 3','block_1':'Block 1','block_6':'Block 6','omit_2020':'Omit 2020','omit_2021':'Omit 2021','omit_2022':'Omit 2022','omit_2023':'Omit 2023','early_2020_2021':'2020--2021','late_2022_2023':'2022--2023','iid_gaussian_log_returns':'IID Gaussian log returns','legacy_mixed_measurement':'Mixed monthly measurement'}
for c in ['ARS','TRY']:
    table('robust_'+c,['Calibration','Liquidated','Loss','CVaR$_{99}$'],[[rl[r.variation],pct(r.expected_liquidated_exposure_share),pct(r.mean_bad_debt_ratio),pct(r.bad_debt_cvar_99)] for r in rob.query('currency==@c').itertuples()], 'lrrr')
s=pd.read_csv(R/'joint_sensitivity.csv')
sum_s=s.groupby(['currency','distribution']).agg(min_loss=('mean_bad_debt_ratio','min'),max_loss=('mean_bad_debt_ratio','max'),min_tail=('bad_debt_cvar_99','min'),max_tail=('bad_debt_cvar_99','max')).reset_index()
table('joint_ranges',['Currency','CR distribution','Min loss','Max loss','Min tail','Max tail'],[[r.currency,esc(r.distribution),pct(r.min_loss),pct(r.max_loss),pct(r.min_tail),pct(r.max_tail)] for r in sum_s.itertuples()], 'llrrrr')
u=pd.read_csv(R/'input_uncertainty.csv');ur=[]
for c in ['ARS','TRY']:
    b=base.query("currency==@c and rate_rule=='adaptive_75'").iloc[0];g=u.query('currency==@c')
    ur.append([c,pct(b.mean_bad_debt_ratio),pct(1.96*b.mc_se_bad_debt),pct(g.mean_bad_debt_ratio.quantile(.025)),pct(g.mean_bad_debt_ratio.quantile(.975)),pct(g.bad_debt_cvar_99.quantile(.025)),pct(g.bad_debt_cvar_99.quantile(.975))])
table('uncertainty',['Currency','Mean loss','MC halfwidth','Input low','Input high','Tail low','Tail high'],ur,'lrrrrrr')
a=pd.read_csv(R/'principal_ablation.csv')
al={'makerdao_principal':'MakerDAO weights','equal_principal':'Equal principal bins','normalized_unit_with_cr_weights':'Normalized CR quadrature','literal_one_dollar_per_cr_point':'One dollar per CR point'}
table('ablation',['Currency','Scheme','Cells','Liquidated','Loss','CVaR$_{99}$'],[[r.currency,al[r.scheme],int(r.synthetic_cells),pct(r.expected_liquidated_exposure_share),pct(r.mean_bad_debt_ratio),pct(r.bad_debt_cvar_99)] for r in a.itertuples()],'llrrrr')
h=pd.read_csv(R/'historical_replay.csv');hr=[]
for c in ['ARS','TRY']:
 for asset in ['ETH','BTC']:
    g=h.query("currency==@c and collateral==@asset and mechanism=='timely'")
    hr.append([c,asset,len(g),pct(g.expected_liquidated_exposure_share.mean()),pct(g.mean_bad_debt_ratio.mean()),pct(g.mean_bad_debt_ratio.max())])
table('historical',['Currency','Collateral','Windows','Mean liq.','Mean loss','Max loss'],hr,'llrrrr')
# Macros and reconciliation share the same source rows and formatter.
mac=[];recon=[]
for c,prefix in [('ARS','Ars'),('TRY','Try')]:
    b=base.query("currency==@c and rate_rule=='adaptive_75'").iloc[0]
    for short,col,where in [('Liq','expected_liquidated_exposure_share','Abstract; tab:main; results'),('Loss','mean_bad_debt_ratio','Abstract; tab:main; results; conclusion'),('Tail','bad_debt_cvar_99','Abstract; tab:main; results'),('Reserve','reserve_breach_10pct','tab:capital; results')]:
        mac.append('\\newcommand{\\'+prefix+short+'}{'+pct(b[col])+r'\%}')
        recon.append(dict(currency=c,scenario='ETH/adaptive_75/timely',metric=col,raw_value=b[col],display_percent=pct(b[col]),locations=where,source='results/main_results.csv'))
    old=rob.query("currency==@c and variation=='legacy_mixed_measurement'").iloc[0]
    mac.append('\\newcommand{\\'+prefix+'MixedLoss}{'+pct(old.mean_bad_debt_ratio)+r'\%}')
(T/'numbers.tex').write_text('\n'.join(mac)+'\n')
pd.DataFrame(recon).to_csv(R/'headline_reconciliation.csv',index=False)
table('reconciliation',['Currency','Metric','Raw ratio','Displayed (\\%)'],[[r['currency'],{'expected_liquidated_exposure_share':'Liquidated exposure','mean_bad_debt_ratio':'Mean credit loss','bad_debt_cvar_99':'CVaR99','reserve_breach_10pct':'10\\% credit budget breach'}[r['metric']],f"{r['raw_value']:.8f}",r['display_percent']] for r in recon],'llrr')
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140})
# Price panel.
p=pd.read_csv('data/processed/joint_monthly_market_panel.csv',parse_dates=['month'])
fig,ax=plt.subplots(1,2,figsize=(10,3.5),layout='constrained')
for col in ['ars_per_usd','try_per_usd']:ax[0].plot(p.month,p[col]/p[col].iloc[0],label=col[:3].upper())
for col in ['eth_usd','btc_usd']:ax[1].plot(p.month,p[col]/p[col].iloc[0],label=col[:3].upper())
for a0,title in zip(ax,['Official FX: LCU per USD','Crypto reference price: USD']):a0.set_title(title);a0.set_ylabel('January 2020 = 1');a0.legend();a0.tick_params(axis='x',rotation=30)
fig.savefig(F/'market_averages.pdf');plt.close(fig)
# Rate/financing trade-off.
fig,ax=plt.subplots(1,2,figsize=(10,3.5),layout='constrained')
for j,c in enumerate(['ARS','TRY']):
    b=base.query('currency==@c')
    ax[j].scatter(b.financing_effect_all*100,b.mean_bad_debt_ratio*100,c=np.arange(6),cmap='viridis',s=50)
    for i,r in enumerate(b.itertuples()):ax[j].annotate(str(i+1),(r.financing_effect_all*100,r.mean_bad_debt_ratio*100),xytext=(4,3),textcoords='offset points')
    ax[j].set(title=c+'/ETH',xlabel='Financing-side net debt effect (%)',ylabel='Mean credit loss / initial principal (%)');ax[j].axvline(0,color='gray',lw=.6)
fig.savefig(F/'policy_tradeoff.pdf');plt.close(fig)
# Joint surface: all 108 parameter combinations per currency in a compact matrix.
for c in ['ARS','TRY']:
    g=s.query('currency==@c').copy()
    g['row']=g.distribution+' / '+g.delay_months.astype(str)+'m'
    rows=[d+' / '+str(delay)+'m' for d in ['base','uniform','near_threshold','buffered'] for delay in [0,1,2]]
    g['column']=[f'{100*h:.0f}/{100*k:.0f}' for h,k in zip(g.base_haircut,g.congestion_slope)]
    cols=[f'{100*h:.0f}/{100*k:.0f}' for h in [.05,.08,.15] for k in [0,.2,.4]]
    mat=g.pivot(index='row',columns='column',values='mean_bad_debt_ratio').reindex(index=rows,columns=cols)*100
    fig,ax=plt.subplots(figsize=(8.6,6.2),layout='constrained');im=ax.imshow(mat,aspect='auto',cmap='YlOrRd',vmin=0,vmax=9)
    ax.tick_params(labelsize=11);ax.set_xticks(range(9),cols);ax.set_yticks(range(12),[x.replace('_',' ') for x in rows]);ax.set_xlabel('Base haircut / congestion slope (%)');ax.set_title(c+'/ETH: mean credit loss (% of initial principal)')
    for i in range(12):
      for j in range(9):ax.text(j,i,f'{mat.iloc[i,j]:.2f}',ha='center',va='center',fontsize=11,color='white' if mat.iloc[i,j]>5 else 'black')
    fig.colorbar(im,ax=ax,shrink=.85,label='Mean loss (%)');fig.savefig(F/('joint_'+c+'.pdf'));plt.close(fig)
print('Generated reporting tables, macros and figures')
