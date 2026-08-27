import httpx, sys, time
base = 'http://127.0.0.1:8000'

ok = []
fail = []

def get(p):
    r = httpx.get(base + p)
    print('GET', p, r.status_code)
    return r

def post(p, j):
    r = httpx.post(base + p, json=j)
    print('POST', p, r.status_code, r.text)
    return r

def patch(p, j):
    r = httpx.patch(base + p, json=j)
    print('PATCH', p, j, r.status_code, r.text)
    return r

print('Health', get('/health').status_code)
print('Docs', get('/docs').status_code)
print('Market', get('/market').status_code)
print('Deals', get('/deals').status_code)
print('Orders', get('/orders').status_code)

# Ensure at least one user
r = get('/users')
users = r.json() if r.status_code == 200 else []
if not users:
    print('No users found, creating a test user')
    r = post('/users', {'company_name':'TEST','name':'tester','email':f'tester{int(time.time())}@example.com','password':'pw','role':'user'})
    if r.status_code == 200:
        users = [r.json()]
    else:
        print('Failed to create user', r.status_code)
        sys.exit(1)

buyer_id = users[0]['id']
print('Using buyer_id', buyer_id)

# Ensure at least one market product
r = get('/market')
products = r.json() if r.status_code == 200 else []
if not products:
    print('No market products, creating product')
    seller_id = buyer_id
    r = post('/products', {'seller_id': seller_id, 'metal':'Copper','grade':'A','quantity':100,'unit':'ton','price':1000,'status':'available'})
    if r.status_code == 200:
        products = [r.json()]
    else:
        print('Failed to create product', r.status_code)
        sys.exit(1)

# accommodate MarketResponse vs ProductResponse
product_id = products[0].get('product_id') or products[0].get('id')
print('Using product_id', product_id)

# 1. Create a deal
r = post('/deals', {'product_id': product_id, 'buyer_id': buyer_id, 'quantity': 1, 'proposed_price': 1000})
if r.status_code != 200:
    print('Deal creation failed', r.status_code)
    fail.append('deal_create')
else:
    deal = r.json()
    did = deal['id']
    print('Created deal', did)

# 2. Try bad inputs
r = post('/deals', {'product_id': product_id, 'buyer_id': buyer_id, 'quantity': 0, 'proposed_price': 1000})
if r.status_code == 400:
    ok.append('bad_quantity_blocked')
else:
    fail.append('bad_quantity')

r = post('/deals', {'product_id': 999999, 'buyer_id': buyer_id, 'quantity': 1, 'proposed_price': 1000})
if r.status_code == 404:
    ok.append('bad_product_blocked')
else:
    fail.append('bad_product')

# 3. Promote deal to AGREED
r = patch(f'/deals/{did}/status', {'status': 'AGREED'})
if r.status_code == 200:
    ok.append('deal_to_agreed')
else:
    fail.append('deal_to_agreed')

# 4. Create order from deal
r = post(f'/deals/{did}/create-order', {})
if r.status_code == 200:
    order = r.json(); oid = order['id']; ok.append('create_order_from_deal'); print('Order created', oid)
else:
    print('Create order failed', r.status_code, r.text); fail.append('create_order_from_deal')

# 5. Duplicate create-order should fail
r = post(f'/deals/{did}/create-order', {})
if r.status_code == 400:
    ok.append('duplicate_create_blocked')
else:
    fail.append('duplicate_create')

# 6. Check GET deal/order
r = get(f'/deals/{did}/order')
if r.status_code == 200:
    ok.append('get_deal_order')
else:
    fail.append('get_deal_order')

# 7. Advance order statuses to COMPLETED
transitions = ['ACCEPTED', 'PAID', 'SHIPPED', 'COMPLETED']
for s in transitions:
    r = patch(f'/orders/{oid}/status', {'status': s})
    if r.status_code == 200:
        print('Order ->', s)
    else:
        print('Failed to set', s, r.status_code, r.text); fail.append(f'set_{s}'); break

# 8. Completion endpoint
r = get(f'/deals/{did}/completion')
if r.status_code == 200 and r.json().get('completed') == True:
    ok.append('completion_true')
else:
    fail.append('completion_check')

# 9. Invalid transition: COMPLETED -> PENDING
r = patch(f'/orders/{oid}/status', {'status': 'PENDING'})
if r.status_code == 400:
    ok.append('invalid_completed_blocked')
else:
    fail.append('invalid_completed')

# 10. Non-existent resources
checks = [('/orders/9999','GET'),('/deals/9999','GET'),('/deals/9999/order','GET'),('/deals/9999/completion','GET')]
for path,method in checks:
    if method == 'GET':
        r = get(path)
    else:
        r = patch(path, {'status':'PENDING'})
    if r.status_code == 404:
        ok.append(f'404_{path}')
    else:
        fail.append(f'no404_{path}')

# 11. POST /orders with invalid refs
r = post('/orders', {'product_id':99999,'buyer_id':99999,'quantity':1,'price':100})
if r.status_code in (400,404):
    ok.append('bad_order_refs_blocked')
else:
    fail.append('bad_order_refs')

print('\nOK tests:', ok)
print('FAIL tests:', fail)

if fail:
    print('Integration tests completed: FAIL')
    sys.exit(2)
else:
    print('Integration tests completed: PASS')
    sys.exit(0)
