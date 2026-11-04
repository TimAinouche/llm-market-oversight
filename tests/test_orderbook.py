from market.orderbook import BUY, SELL, OrderBook


def test_ordre_limite_sans_croisement_reste_dans_le_carnet():
    ob = OrderBook()
    ob.submit_limit("A", BUY, 99, 10)
    ob.submit_limit("B", SELL, 101, 10)
    assert ob.best_bid() == 99
    assert ob.best_ask() == 101
    assert ob.spread() == 2
    assert ob.trades == []


def test_ordre_qui_croise_s_execute_au_prix_passif():
    ob = OrderBook()
    ob.submit_limit("A", SELL, 100, 10)
    _, trades = ob.submit_limit("B", BUY, 102, 10)   # acheteur prêt à payer plus
    assert len(trades) == 1
    assert trades[0].price == 100                    # prix de l'ordre déjà dans le carnet
    assert trades[0].buyer == "B" and trades[0].seller == "A"
    assert ob.best_ask() is None and ob.best_bid() is None


def test_execution_partielle():
    ob = OrderBook()
    ob.submit_limit("A", SELL, 100, 10)
    _, trades = ob.submit_limit("B", BUY, 100, 4)
    assert trades[0].qty == 4
    assert ob.depth()["asks"] == [(100, 6)]          # il reste 6 à la vente


def test_reste_d_un_ordre_limite_va_dans_le_carnet():
    ob = OrderBook()
    ob.submit_limit("A", SELL, 100, 3)
    ob.submit_limit("B", BUY, 100, 10)
    assert ob.best_bid() == 100
    assert ob.depth()["bids"] == [(100, 7)]


def test_priorite_prix_puis_temps():
    ob = OrderBook()
    ob.submit_limit("lent", SELL, 100, 5)
    ob.submit_limit("rapide", SELL, 100, 5)          # même prix, arrivé après
    ob.submit_limit("cher", SELL, 101, 5)
    _, trades = ob.submit_market("X", BUY, 12)
    assert [t.seller for t in trades] == ["lent", "rapide", "cher"]
    assert [t.price for t in trades] == [100, 100, 101]


def test_ordre_au_marche_sur_carnet_vide_ne_fait_rien():
    ob = OrderBook()
    _, trades = ob.submit_market("X", BUY, 5)
    assert trades == []
    assert ob.best_bid() is None                     # un ordre au marché ne reste jamais


def test_annulation():
    ob = OrderBook()
    oid, _ = ob.submit_limit("A", BUY, 99, 10)
    assert ob.cancel(oid) is True
    assert ob.best_bid() is None
    assert ob.cancel(oid) is False                   # déjà annulé


def test_on_ne_peut_pas_annuler_un_ordre_execute():
    ob = OrderBook()
    oid, _ = ob.submit_limit("A", SELL, 100, 5)
    ob.submit_market("B", BUY, 5)
    assert ob.cancel(oid) is False
