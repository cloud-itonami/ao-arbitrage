(ns arbitrage-worker.app-test
  (:require [cljs.test :refer [deftest is testing use-fixtures]]
            [re-frame.core :as rf]
            [re-frame.db :as rf-db]
            [arbitrage-worker.app :as app]))

;; re-frame keeps its db in a global atom (re-frame.db/app-db). Reset it
;; around each test so events fired in one test can't leak into the next.
(use-fixtures :each
  {:before (fn [] (reset! rf-db/app-db {}))})

(deftest initialize-db-sets-defaults
  (testing "::initialize-db seeds the same defaults the Svelte scaffold had"
    (rf/dispatch-sync [::app/initialize-db])
    (is (= "Worker" @(rf/subscribe [::app/title])))
    (is (= "etzhayyim-project-arbitrage" @(rf/subscribe [::app/project])))
    (is (= "worker" @(rf/subscribe [::app/name])))
    (is (= "worker" @(rf/subscribe [::app/kind])))
    (is (= 0 @(rf/subscribe [::app/route-count])))
    (is (= [] @(rf/subscribe [::app/routes])))
    (is (= [] @(rf/subscribe [::app/vars])))
    (is (true? @(rf/subscribe [::app/xrpc?])))
    (is (string? @(rf/subscribe [::app/relative-path])))))

(deftest app-view-renders-hiccup
  (testing "app-view returns a hiccup vector rooted at the DADS container"
    (rf/dispatch-sync [::app/initialize-db])
    (let [hiccup (app/app-view)]
      (is (vector? hiccup))
      (is (= :div (first hiccup)))
      (is (= "dds-ext-container" (:class (second hiccup)))))))

(deftest routes-panel-shows-empty-message-when-no-routes
  (testing "empty :routes renders the same fallback text the Svelte {:else} branch had"
    (let [panel (#'app/routes-panel [])
          rendered (pr-str panel)]
      (is (re-find #"No public route is declared next to this app surface\." rendered)))))

(deftest routes-panel-lists-routes-when-present
  (testing "non-empty :routes renders one <li> per route instead of the fallback"
    (let [panel (#'app/routes-panel ["/xrpc/com.example.ping"])
          rendered (pr-str panel)]
      (is (re-find #"/xrpc/com\.example\.ping" rendered))
      (is (not (re-find #"No public route is declared" rendered))))))

(deftest vars-panel-shows-empty-message-when-no-vars
  (testing "empty :vars renders the same fallback text the Svelte {:else} branch had"
    (let [panel (#'app/vars-panel [])
          rendered (pr-str panel)]
      (is (re-find #"No public vars are declared in the nearest wrangler config\." rendered)))))

(deftest vars-panel-lists-chips-when-present
  (testing "non-empty :vars renders one chip-label per var instead of the fallback"
    (let [panel (#'app/vars-panel ["AGENTGATEWAY_MCP_ROUTER_URL"])
          rendered (pr-str panel)]
      (is (re-find #"AGENTGATEWAY_MCP_ROUTER_URL" rendered))
      (is (not (re-find #"No public vars are declared" rendered))))))
