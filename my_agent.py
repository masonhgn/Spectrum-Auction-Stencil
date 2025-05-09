# smart_bidder.py
from agt_server.agents.base_agents.lsvm_agent import MyLSVMAgent
from agt_server.local_games.lsvm_arena import LSVMArena
from agt_server.agents.test_agents.lsvm.min_bidder.my_agent import MinBidAgent
from agt_server.agents.test_agents.lsvm.jump_bidder.jump_bidder import JumpBidder
from agt_server.agents.test_agents.lsvm.truthful_bidder.my_agent import TruthfulBidder

import numpy as np, heapq, time

NAME = "CJM"

ALPHA_INIT= 0.7 #aggression in round 0
DEFEND_FRAC=0.3 #how hard to defend a held good
REOPT_INTERVAL=25 #rounds between 1 swap local searches
EPS= 0.1  #min bid tick

class MyAgent(MyLSVMAgent):



    def setup(self):
        self.round=0
        self.goods=list(self.get_goods()) 
        self.target=set()








    # HELPER FUNCTIONS 
    def _bundle_util(self, bundle):
        return self.calc_total_utility(bundle)

    def _marginal_gain(self, bundle, g, min_bids):
        with_g = bundle | {g}
        return self._bundle_util(with_g) - self._bundle_util(bundle) - min_bids[g]

    








    def get_bids(self):
        min_bids=self.get_min_bids()
        alloc=set(self.get_tentative_allocation())
        bids={}

        #STAKE INITIAL CLAIM
        if self.round == 0:
            self.target = self._initial_target(min_bids)
            for g in self.target:
                bids[g] = min_bids[g]+ALPHA_INIT*(self.get_valuation(g) - min_bids[g])
            return self.clip_bids(bids)

        #DEFEND
        for g in alloc:
            delta = self._marginal_gain(alloc, g, min_bids) + min_bids[g]
            if delta > EPS:
                bids[g] = min_bids[g] + DEFEND_FRAC * delta

        #SNIPE
        for g in self.goods:
            if g in alloc: continue
            mg = self._marginal_gain(alloc, g, min_bids)
            if mg > 0:
                bids[g] = min_bids[g] + 0.5 * mg

        bids = self.clip_bids(bids)
        if not self.is_valid_bid_bundle(bids):
            bids.clear() #FALL BACK






        #REOPTIMIZE EVERY ONCE IN A WHILE
        if self.round % REOPT_INTERVAL == 0:
            self._retarget(min_bids, alloc)

        return bids






    def update(self):
        self.round += 1









    #SEARCHES
    def _initial_target(self, min_bids):
        limit= 12 if self.is_national_bidder() else 6
        roi_heap = [(-(self.get_valuation(g) - min_bids[g]), g) for g in self.goods]
        heapq.heapify(roi_heap)

        bundle = set()
        while roi_heap and len(bundle) < limit:
            _, g = heapq.heappop(roi_heap)
            bundle.add(g)
        return bundle

    def _retarget(self, min_bids, alloc):
        best_gain, add, drop = 0, None, None
        for g_add in self.goods:
            if g_add in alloc: continue
            gain_add = self._marginal_gain(alloc, g_add, min_bids)
            if gain_add <= 0: continue

            #build the hypothetical bundle after the swap
            for g_drop in alloc:
                new_bundle = alloc - {g_drop} | {g_add}
                util_gain  = self._bundle_util(new_bundle) - self._bundle_util(alloc)

                #track the best swap found so far
                if util_gain > best_gain:
                    best_gain, add, drop = util_gain, g_add, g_drop
        if best_gain > 0:
            #remove worse good and insert better one in target set
            self.target.discard(drop)
            self.target.add(add)

################### SUBMISSION #####################
my_agent_submission = MyAgent(NAME)
####################################################

if __name__ == "__main__":

    ### DO NOT TOUCH THIS #####
    agent = MyAgent(NAME)
    arena = LSVMArena(
        num_cycles_per_player = 3,
        timeout       = 1,
        local_save_path="saved_games",
        players=[
            agent,
            MyAgent("CP - MyAgent"),
            MyAgent("CP2 - MyAgent"),
            MyAgent("CP3 - MyAgent"),
            MinBidAgent("Min Bidder"),
            JumpBidder("Jump Bidder"),
            TruthfulBidder("Truthful Bidder"),
        ]
    )

    start = time.time()
    arena.run()
    end = time.time()
