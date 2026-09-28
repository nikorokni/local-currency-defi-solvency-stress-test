import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'analysis'))
import numpy as np
import pandas as pd
from stress_test import *

class ModelTests(unittest.TestCase):
    def test_strict_threshold_and_no_loss(self):
        p=np.zeros((1,14,2));p[:,:,0]=.2/12
        r,_,a=simulate_portfolio(p,'static_20',grid=np.array([1.5]))
        self.assertEqual(r['breach_exposure_share'],0)
        self.assertAlmostEqual(r['mean_bad_debt_ratio'],0)
        self.assertAlmostEqual(r['financing_effect_all'],0)
    def test_last_month_breach_is_pending_then_closed(self):
        p=np.zeros((1,14,2));p[:,:,0]=.2/12;p[:,11,1]=-.8
        r,_,a=simulate_portfolio(p,'static_20',Mechanism('delay',1,0,0),grid=np.array([2.]))
        self.assertEqual(r['executed_by_month12_share'],0)
        self.assertEqual(r['pending_at_month12_share'],1)
        self.assertEqual(r['terminal_undercollateralized_share'],1)
        self.assertAlmostEqual(r['mean_bad_debt_ratio'],.6)
    def test_irrevocable_breach_even_if_price_recovers(self):
        p=np.zeros((1,14,2));p[:,:,0]=.2/12;p[:,0,1]=-.6;p[:,1,1]=2
        r,_,a=simulate_portfolio(p,'static_20',Mechanism('delay',1,0,0),grid=np.array([2.]))
        self.assertEqual(r['breach_exposure_share'],1)
        self.assertEqual(r['mean_bad_debt_ratio'],0)
        self.assertAlmostEqual(a['penalty'][0,0],.13)
        self.assertAlmostEqual(a['returned'][0,0],1.27)
    def test_debt_accrues_during_delay(self):
        p=np.zeros((1,14,2));p[:,0,1]=-.8
        _,_,a=simulate_portfolio(p,'static_20',Mechanism('delay',1),grid=np.array([2.]))
        self.assertAlmostEqual(a['debt'][0,0],(1+.2/12)**2)
    def test_auction_cash_conservation_and_equity_identity(self):
        p=moving_block_bootstrap(np.array([[.03,-.4],[.02,.3],[.1,-.2]]),60,14,2,np.random.default_rng(4))
        r,_,a=simulate_portfolio(p,mechanism=Mechanism('delay',2))
        h=a['has'];proceeds=a['collateral']*(1-a['haircut'])
        np.testing.assert_allclose((a['recovery']+a['penalty']+a['returned'])[h],proceeds[h],atol=1e-12)
        np.testing.assert_allclose(a['cohort_bad'],a['debt']-a['recovery'],atol=1e-12)
        np.testing.assert_allclose(a['financing'][h],(1-a['collateral']+a['returned'])[h],atol=1e-12)
        f=a['fx'][np.arange(60)[:,None],a['settled']]
        bridge=.1+((a['debt']-1/f-a['cohort_bad']+a['penalty'])*a['weights']).sum(1)
        np.testing.assert_allclose(bridge,a['ledger'][:,-1],atol=1e-12)
    def test_no_rate_lookahead_and_governance_limit(self):
        a=np.full((2,14),.1);b=a.copy();b[:,8:]=.7
        for rule in RATE_RULES:
            np.testing.assert_allclose(annual_rate_path(a,rule)[:,:9],annual_rate_path(b,rule)[:,:9])
        self.assertLessEqual(np.abs(np.diff(annual_rate_path(a,'partial_adjust'))).max(),.05+1e-12)
    def test_bootstrap_never_bridges_missing_year(self):
        dates=pd.to_datetime(['2020-10-01','2020-11-01','2020-12-01','2022-01-01','2022-02-01','2022-03-01'])
        d=np.column_stack([np.arange(6),np.arange(6)])
        p=moving_block_bootstrap(d,100,5,3,np.random.default_rng(1),dates)
        for x in p: self.assertIn(tuple(x[:3,0]),[(0,1,2),(3,4,5)])
        self.assertEqual(p.shape,(100,5,2))
    def test_aggregation_invariance(self):
        grid,w=collateral_distribution();pw=np.array([.01,.09,.9])
        np.testing.assert_allclose(np.outer(pw,w).sum(0),w,atol=1e-15)
    def test_common_random_main_robustness_and_reconciliation(self):
        m=pd.read_csv('results/main_results.csv');r=pd.read_csv('results/robustness.csv')
        for currency in ['ARS','TRY']:
            x=m.query("currency==@currency and collateral=='ETH' and mechanism=='timely' and rate_rule=='adaptive_75'").iloc[0]
            y=r.query("currency==@currency and variation=='block_3'").iloc[0]
            self.assertEqual(x.mean_bad_debt_ratio,y.mean_bad_debt_ratio)
        np.testing.assert_allclose(m.breach_exposure_share,m.executed_by_month12_share+m.pending_at_month12_share,atol=2e-12)
        np.testing.assert_allclose(m.financing_effect_all,m.financing_effect_survivors*m.survivor_exposure_share+m.financing_effect_liquidated*(1-m.survivor_exposure_share),atol=2e-11)
        self.assertTrue((m.bad_debt_cvar_99>=m.mean_bad_debt_ratio).all())
if __name__=='__main__':unittest.main()
