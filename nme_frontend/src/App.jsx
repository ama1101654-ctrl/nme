import React, { useEffect, useState } from 'react'

// API base. Change via Vite env: VITE_API_URL or default to backend address.
const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const AUTH_TOKEN_STORAGE_KEY = 'nme_auth_token'
const REFRESH_TOKEN_STORAGE_KEY = 'nme_refresh_token'
const AUTH_STORAGE_KEY = 'nme_auth_user_id'

// MVP 현재 사용자 기본값(향후 로그인 사용자 id 주입으로 교체 예정)
const DEFAULT_USER_ID = 2

function resolveBootstrapUserId(){
  // STEP 27: auth 도입 전까지는 env 또는 기본 user id로 bootstrap한다.
  // 실제 인증 도입 시 이 지점만 교체하면 나머지 currentUser 흐름은 그대로 재사용 가능하다.
  const raw = import.meta.env.VITE_BOOTSTRAP_USER_ID
  if(!raw) return DEFAULT_USER_ID

  const parsed = Number(raw)
  if(Number.isInteger(parsed) && parsed > 0){
    return parsed
  }

  console.warn('Invalid VITE_BOOTSTRAP_USER_ID. Fallback to DEFAULT_USER_ID:', raw)
  return DEFAULT_USER_ID
}

const BOOTSTRAP_USER_ID = resolveBootstrapUserId()

function isValidUserId(value){
  return Number.isInteger(value) && value > 0
}

function readAuthenticatedUserIdFromStorage(){
  if(typeof window === 'undefined') return null

  try{
    const raw = window.sessionStorage.getItem(AUTH_STORAGE_KEY)
    if(!raw) return null

    const parsed = Number(raw)
    return isValidUserId(parsed) ? parsed : null
  }catch(err){
    console.error('Auth storage read error', err)
    return null
  }
}

function readAuthTokenFromStorage(){
  if(typeof window === 'undefined') return null

  try{
    return window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || null
  }catch(err){
    console.error('Auth token storage read error', err)
    return null
  }
}

function readRefreshTokenFromStorage(){
  if(typeof window === 'undefined') return null

  try{
    return window.sessionStorage.getItem(REFRESH_TOKEN_STORAGE_KEY) || null
  }catch(err){
    console.error('Refresh token storage read error', err)
    return null
  }
}

function storeAuthToken(token){
  if(typeof window === 'undefined') return

  try{
    window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token)
  }catch(err){
    console.error('Auth token storage write error', err)
  }
}

function storeRefreshToken(token){
  if(typeof window === 'undefined') return

  try{
    window.sessionStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token)
  }catch(err){
    console.error('Refresh token storage write error', err)
  }
}

function storeAuthenticatedUserId(userId){
  if(typeof window === 'undefined') return

  try{
    window.sessionStorage.setItem(AUTH_STORAGE_KEY, String(userId))
  }catch(err){
    console.error('Auth storage write error', err)
  }
}

function clearAuthenticatedUserId(){
  if(typeof window === 'undefined') return

  try{
    window.sessionStorage.removeItem(AUTH_STORAGE_KEY)
  }catch(err){
    console.error('Auth storage clear error', err)
  }
}

function clearAuthToken(){
  if(typeof window === 'undefined') return

  try{
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
  }catch(err){
    console.error('Auth token storage clear error', err)
  }
}

function clearRefreshToken(){
  if(typeof window === 'undefined') return

  try{
    window.sessionStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
  }catch(err){
    console.error('Refresh token storage clear error', err)
  }
}

function resolveAuthenticatedUserId(){
  // STEP 32: 인증 여부는 JWT token으로 판단하되, user id는 하위 호환용 저장값을 재사용한다.
  if(!readAuthTokenFromStorage()) return null
  return readAuthenticatedUserIdFromStorage()
}

function resolveAuthenticationContext(){
  const authenticatedUserId = resolveAuthenticatedUserId()
  const token = readAuthTokenFromStorage()

  if(token){
    return {
      status: 'authenticated',
      source: 'auth',
      token,
      userId: isValidUserId(authenticatedUserId) ? authenticatedUserId : null
    }
  }

  return {
    status: 'unauthenticated',
    source: 'none',
    token: null,
    userId: null
  }
}

function resolveCurrentUserId(authContext = resolveAuthenticationContext()){
  if(authContext.status === 'authenticated' && isValidUserId(authContext.userId)){
    return authContext.userId
  }

  return BOOTSTRAP_USER_ID
}

function resolveCurrentUserBootstrapContext(){
  const authContext = resolveAuthenticationContext()
  const userId = resolveCurrentUserId(authContext)
  const currentUserAuthContext = authContext.status === 'authenticated'
    ? authContext
    : {
        status: 'bootstrap',
        source: 'bootstrap',
        userId
      }

  return {
    authContext: currentUserAuthContext,
    userId,
    fallbackUser: getFallbackCurrentUser(userId)
  }
}

function buildAuthLoginUrl(){
  return API + '/auth/login'
}

function buildAuthMeUrl(){
  return API + '/auth/me'
}

function buildAuthRefreshUrl(){
  return API + '/auth/refresh'
}

function buildAuthLogoutUrl(){
  return API + '/auth/logout'
}

function getFallbackCurrentUser(userId){
  if(userId === 3){
    return {
      id: 3,
      role: 'SELLER',
      name: 'MVP Seller'
    }
  }

  return {
    id: userId,
    role: 'BUYER',
    name: 'MVP Buyer'
  }
}

const USER_ROLE_LABEL = {
  BUYER: '구매자',
  SELLER: '판매자',
  ADMIN: '관리자',
  USER: '일반 사용자'
}

const USER_ROLE_CODE = {
  BUYER: 'Buyer',
  SELLER: 'Seller',
  ADMIN: 'Admin',
  USER: 'User'
}

const ORDER_NEXT_ACTION = {
  PENDING: {
    nextStatus: 'ACCEPTED',
    buttonLabel: '주문 승인',
    confirmMessage: '주문을 승인하시겠습니까?',
    successMessage: '주문이 승인되었습니다.'
  },
  ACCEPTED: {
    nextStatus: 'PAID',
    buttonLabel: '결제 완료',
    confirmMessage: '결제를 완료 처리하시겠습니까?',
    successMessage: '결제가 완료 처리되었습니다.'
  },
  PAID: {
    nextStatus: 'SHIPPED',
    buttonLabel: '출하 처리',
    confirmMessage: '출하 처리하시겠습니까?',
    successMessage: '출하 상태로 변경되었습니다.'
  },
  SHIPPED: {
    nextStatus: 'COMPLETED',
    buttonLabel: '거래 완료',
    confirmMessage: '거래를 완료 처리하시겠습니까?',
    successMessage: '거래가 완료되었습니다.'
  }
}

const ORDER_PROGRESS = [
  { status: 'PENDING', label: '① 주문 생성' },
  { status: 'ACCEPTED', label: '② 주문 승인' },
  { status: 'PAID', label: '③ 결제' },
  { status: 'SHIPPED', label: '④ 출하' },
  { status: 'COMPLETED', label: '⑤ 완료' }
]

function getStatusClass(status){
  return `status-${String(status || '').toLowerCase()}`
}

function isProgressDone(currentStatus, stepStatus){
  const order = ['PENDING', 'ACCEPTED', 'PAID', 'SHIPPED', 'COMPLETED']
  const currentIndex = order.indexOf(currentStatus)
  const stepIndex = order.indexOf(stepStatus)
  if(currentIndex < 0 || stepIndex < 0) return false
  return stepIndex <= currentIndex
}

const DEAL_STATUS_LABEL = {
  NEGOTIATING: '협의중',
  AGREED: '거래 승인',
  REJECTED: '거래 거절',
  CANCELLED: '거래 취소'
}

const ORDER_STATUS_LABEL = {
  PENDING: '주문 대기',
  ACCEPTED: '주문 승인',
  PAID: '결제 완료',
  SHIPPED: '배송 완료',
  COMPLETED: '거래 완료',
  CANCELLED: '주문 취소'
}

function labelDealStatus(status){
  return DEAL_STATUS_LABEL[status] || status || '-'
}

function labelOrderStatus(status){
  return ORDER_STATUS_LABEL[status] || status || '-'
}

function labelUserRole(role){
  const normalizedRole = String(role || '').toUpperCase()
  return USER_ROLE_LABEL[normalizedRole] || role || '-'
}

function labelUserCode(role){
  const normalizedRole = String(role || '').toUpperCase()
  return USER_ROLE_CODE[normalizedRole] || 'User'
}

function isBuyerRole(role){
  return String(role || '').toUpperCase() === 'BUYER'
}

function isSellerRole(role){
  return String(role || '').toUpperCase() === 'SELLER'
}

function buildUserUrl(userId){
  return API + `/users/${userId}`
}

const CURRENT_USER_CACHE = new Map()
const CURRENT_USER_PROMISE_CACHE = new Map()
const AUTH_ME_CACHE = new Map()
const AUTH_ME_PROMISE_CACHE = new Map()
let AUTH_REFRESH_PROMISE = null

function getUserLoadErrorMessage(status, detail){
  if(status === 404) return detail || '현재 사용자를 찾을 수 없습니다.'
  if(status === 422) return detail || '현재 사용자 조회 요청 형식이 올바르지 않습니다.'
  if(status >= 500) return detail || '현재 사용자 조회 중 서버 오류가 발생했습니다.'
  return detail || '현재 사용자 정보를 불러오지 못했습니다.'
}

function getCurrentUserRuntimeErrorMessage(err){
  if(err?.status) return err.message || '현재 사용자 정보를 불러오지 못했습니다.'
  if(err instanceof TypeError) return '현재 사용자 API에 연결할 수 없습니다. 기본 사용자 정보로 계속합니다.'
  return err?.message || '현재 사용자 정보를 불러오지 못했습니다. 기본 사용자 정보로 계속합니다.'
}

function getAuthMeLoadErrorMessage(status, detail){
  if(status === 401) return detail || '로그인이 필요합니다.'
  if(status === 404) return detail || '현재 인증 사용자를 찾을 수 없습니다.'
  if(status >= 500) return detail || '인증 사용자 조회 중 서버 오류가 발생했습니다.'
  return detail || '인증 사용자 정보를 불러오지 못했습니다.'
}

function normalizeCurrentUser(data){
  if(typeof data?.id !== 'number' || !data?.name || !data?.role){
    throw new Error('현재 사용자 응답 형식이 올바르지 않습니다.')
  }

  return {
    id: data.id,
    name: data.name,
    role: data.role
  }
}

function clearAuthSessionStorage(){
  clearAuthToken()
  clearRefreshToken()
  clearAuthenticatedUserId()
}

async function refreshAccessToken(){
  if(AUTH_REFRESH_PROMISE){
    return AUTH_REFRESH_PROMISE
  }

  AUTH_REFRESH_PROMISE = (async ()=>{
    const refreshToken = readRefreshTokenFromStorage()
    if(!refreshToken){
      const error = new Error('로그인이 필요합니다.')
      error.status = 401
      throw error
    }

    const res = await fetch(buildAuthRefreshUrl(), {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ refresh_token: refreshToken })
    })

    if(!res.ok){
      const j = await res.json().catch(()=>({detail: res.statusText}))
      const error = new Error(getAuthMeLoadErrorMessage(res.status, j.detail))
      error.status = res.status
      throw error
    }

    const data = await res.json()
    if(!data?.access_token || !data?.refresh_token){
      throw new Error('토큰 갱신 응답 형식이 올바르지 않습니다.')
    }

    storeAuthToken(data.access_token)
    storeRefreshToken(data.refresh_token)
    return data.access_token
  })()

  try{
    return await AUTH_REFRESH_PROMISE
  }finally{
    AUTH_REFRESH_PROMISE = null
  }
}

async function authFetch(url, options = {}, retryOnAuthFailure = true){
  const headers = new Headers(options.headers || {})
  const token = readAuthTokenFromStorage()
  if(token){
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if(response.status !== 401 || !retryOnAuthFailure || url === buildAuthRefreshUrl()){
    return response
  }

  await refreshAccessToken()

  const retryHeaders = new Headers(options.headers || {})
  const nextToken = readAuthTokenFromStorage()
  if(nextToken){
    retryHeaders.set('Authorization', `Bearer ${nextToken}`)
  }

  return fetch(url, {
    ...options,
    headers: retryHeaders,
  })
}

async function fetchAuthenticatedCurrentUser(userId){
  const token = readAuthTokenFromStorage()
  const cacheKey = token || `no-token-${userId || 'unknown'}`

  if(AUTH_ME_CACHE.has(cacheKey)){
    return AUTH_ME_CACHE.get(cacheKey)
  }

  if(AUTH_ME_PROMISE_CACHE.has(cacheKey)){
    return AUTH_ME_PROMISE_CACHE.get(cacheKey)
  }

  const request = (async ()=>{
    if(!token){
      const error = new Error('로그인이 필요합니다.')
      error.status = 401
      throw error
    }

    const res = await authFetch(buildAuthMeUrl())

    if(!res.ok){
      const j = await res.json().catch(()=>({detail: res.statusText}))
      const error = new Error(getAuthMeLoadErrorMessage(res.status, j.detail))
      error.status = res.status
      throw error
    }

    const data = normalizeCurrentUser(await res.json())
    AUTH_ME_CACHE.set(cacheKey, data)
    CURRENT_USER_CACHE.set(data.id, data)
    return data
  })()

  AUTH_ME_PROMISE_CACHE.set(cacheKey, request)

  try{
    return await request
  }finally{
    AUTH_ME_PROMISE_CACHE.delete(cacheKey)
  }
}

async function fetchCurrentUserById(userId){
  if(CURRENT_USER_CACHE.has(userId)){
    return CURRENT_USER_CACHE.get(userId)
  }

  if(CURRENT_USER_PROMISE_CACHE.has(userId)){
    return CURRENT_USER_PROMISE_CACHE.get(userId)
  }

  const request = (async ()=>{
    const res = await fetch(buildUserUrl(userId))
    if(!res.ok){
      const j = await res.json().catch(()=>({detail: res.statusText}))
      const error = new Error(getUserLoadErrorMessage(res.status, j.detail))
      error.status = res.status
      throw error
    }

    const normalizedUser = normalizeCurrentUser(await res.json())
    CURRENT_USER_CACHE.set(userId, normalizedUser)
    return normalizedUser
  })()

  CURRENT_USER_PROMISE_CACHE.set(userId, request)

  try{
    return await request
  }finally{
    CURRENT_USER_PROMISE_CACHE.delete(userId)
  }
}

function buildDealsUrl(){
  // STEP 25: GET /deals does not accept CURRENT_USER-based query params.
  // Buyer/Seller scoping remains a frontend concern until authentication exists.
  return API + '/deals'
}

function getDealsLoadErrorMessage(status, detail){
  if(status === 422) return detail || 'GET /deals 요청 형식이 올바르지 않습니다.'
  if(status === 404) return detail || '거래 조회 API를 찾을 수 없습니다.'
  if(status >= 500) return detail || '거래 조회 중 서버 오류가 발생했습니다.'
  return detail || '거래 정보를 불러오지 못했습니다.'
}

function formatDateTime(v){
  if(!v) return '-'
  const d = new Date(v)
  if(Number.isNaN(d.getTime())) return String(v)
  return d.toLocaleString('ko-KR')
}

function hasOrderStatusAtLeast(status, target){
  const order = ['PENDING', 'ACCEPTED', 'PAID', 'SHIPPED', 'COMPLETED']
  const currentIndex = order.indexOf(status)
  const targetIndex = order.indexOf(target)
  if(currentIndex < 0 || targetIndex < 0) return false
  return currentIndex >= targetIndex
}

function getTradeContext(item){
  const dealStatus = item?.deal?.status
  const orderStatus = item?.order?.status
  const hasOrder = Boolean(item?.order)
  const completed = Boolean(item?.completed)
  return { dealStatus, orderStatus, hasOrder, completed }
}

function getActionState(item){
  const { dealStatus, orderStatus, hasOrder, completed } = getTradeContext(item)

  if(orderStatus === 'COMPLETED' || completed){
    return {
      tone: 'done',
      title: '거래 완료',
      shortStatus: '거래 완료',
      description: '거래가 정상적으로 완료되었습니다.',
      currentStep: '⑦ 거래 완료',
      nextStep: '모든 거래 절차 완료',
      required: false,
      actionType: null,
      actionLabel: null,
      helper: '모든 거래 절차가 완료되었습니다.'
    }
  }

  if(orderStatus === 'CANCELLED'){
    return {
      tone: 'ended',
      title: '거래가 취소되었습니다.',
      shortStatus: '거래 취소',
      description: '주문이 취소되어 현재 거래는 종료되었습니다.',
      currentStep: '거래 취소',
      nextStep: '없음',
      required: false,
      actionType: null,
      actionLabel: null,
      helper: '새로운 거래를 원하시면 Market에서 다른 상품을 선택해 거래를 시작할 수 있습니다.'
    }
  }

  if(dealStatus === 'REJECTED'){
    return {
      tone: 'ended',
      title: '거래 거절',
      shortStatus: '거래 종료',
      description: '거래가 거절되었습니다.',
      currentStep: '거래 종료',
      nextStep: '추가 진행 없음',
      required: false,
      actionType: null,
      actionLabel: null
    }
  }

  if(dealStatus === 'CANCELLED'){
    return {
      tone: 'ended',
      title: '거래가 취소되었습니다.',
      shortStatus: '거래 종료',
      description: '거래가 취소되어 현재 거래는 종료되었습니다.',
      currentStep: '거래 취소',
      nextStep: '없음',
      required: false,
      actionType: null,
      actionLabel: null,
      helper: '새로운 거래를 원하시면 Market에서 다른 상품을 선택해 거래를 시작할 수 있습니다.'
    }
  }

  if(dealStatus === 'NEGOTIATING'){
    return {
      tone: 'waiting',
      title: '거래 승인 대기',
      shortStatus: '승인 대기',
      description: '상대방의 거래 승인을 기다리고 있습니다.',
      currentStep: '① 거래 제안',
      nextStep: '② 거래 승인',
      required: false,
      actionType: null,
      actionLabel: null,
      helper: '거래가 승인되면 주문을 생성할 수 있습니다.'
    }
  }

  if(dealStatus === 'AGREED' && !hasOrder){
    return {
      tone: 'required',
      title: '주문 생성 가능',
      shortStatus: '주문 생성 가능',
      description: '거래가 승인되었습니다.',
      currentStep: '② 거래 승인 완료',
      nextStep: '③ 주문 생성',
      required: true,
      actionType: 'create-order',
      actionLabel: '주문 생성'
    }
  }

  if(orderStatus === 'PENDING'){
    return {
      tone: 'waiting',
      title: '주문 승인 대기',
      shortStatus: '주문 승인 대기',
      description: '주문 승인 대기 중입니다.',
      currentStep: '③ 주문 생성 완료',
      nextStep: '④ 주문 승인',
      required: false,
      actionType: null,
      actionLabel: null,
      helper: '주문이 승인되면 결제를 진행할 수 있습니다.'
    }
  }

  if(orderStatus === 'ACCEPTED'){
    return {
      tone: 'required',
      title: '결제 진행 가능',
      shortStatus: '결제 준비',
      description: '주문이 승인되었습니다.',
      currentStep: '④ 주문 승인 완료',
      nextStep: '⑤ 결제',
      required: true,
      actionType: 'payment-ready',
      actionLabel: '결제 준비'
    }
  }

  if(orderStatus === 'PAID'){
    return {
      tone: 'waiting',
      title: '배송 대기',
      shortStatus: '배송 대기',
      description: '결제가 완료되었습니다.',
      currentStep: '⑤ 결제 완료',
      nextStep: '⑥ 배송',
      required: false,
      actionType: null,
      actionLabel: null,
      helper: '배송을 기다리고 있습니다.'
    }
  }

  if(orderStatus === 'SHIPPED'){
    return {
      tone: 'shipping',
      title: '배송 진행 중',
      shortStatus: '배송 중',
      description: '상품이 배송 중입니다.',
      currentStep: '⑥ 배송 진행',
      nextStep: '⑦ 거래 완료',
      required: false,
      actionType: null,
      actionLabel: null,
      helper: '배송 완료 후 거래가 완료됩니다.'
    }
  }

  return {
    tone: 'waiting',
    title: '상태 확인 필요',
    shortStatus: '확인 필요',
    description: '현재 상태를 확인해 주세요.',
    currentStep: '-',
    nextStep: '-',
    required: false,
    actionType: null,
    actionLabel: null
  }
}

function buildTradeFlowSteps(item){
  const { dealStatus, orderStatus, hasOrder } = getTradeContext(item)

  const steps = [
    { key: 'deal_created', label: '① 거래 제안', done: true },
    { key: 'deal_agreed', label: '② 거래 승인', done: dealStatus === 'AGREED' || hasOrder },
    { key: 'order_created', label: '③ 주문 생성', done: hasOrder },
    { key: 'order_accepted', label: '④ 주문 승인', done: hasOrderStatusAtLeast(orderStatus, 'ACCEPTED') },
    { key: 'order_paid', label: '⑤ 결제', done: hasOrderStatusAtLeast(orderStatus, 'PAID') },
    { key: 'order_shipped', label: '⑥ 배송', done: hasOrderStatusAtLeast(orderStatus, 'SHIPPED') },
    { key: 'trade_completed', label: '⑦ 거래 완료', done: item.completed }
  ]

  const terminalDeal = dealStatus === 'REJECTED' || dealStatus === 'CANCELLED'
  const terminalOrder = orderStatus === 'CANCELLED'

  let currentIndex = -1
  if(item.completed){
    currentIndex = 6
  }else if(!terminalDeal && !terminalOrder){
    currentIndex = steps.findIndex(s => !s.done)
    if(currentIndex < 0) currentIndex = steps.length - 1
  }

  return steps.map((s, idx) => ({
    ...s,
    state: idx === currentIndex ? 'current' : s.done ? 'done' : 'todo'
  }))
}

function getFlowTerminalNote(item){
  const { dealStatus, orderStatus } = getTradeContext(item)
  if(orderStatus === 'CANCELLED'){
    return '🔴 거래 취소됨'
  }
  if(dealStatus === 'CANCELLED'){
    return '🔴 거래 취소됨'
  }
  if(dealStatus === 'REJECTED'){
    return '🔴 거래 거절됨'
  }
  return null
}

function getActionQueueItem(item){
  const { dealStatus, orderStatus, hasOrder, completed } = getTradeContext(item)

  if(completed || orderStatus === 'COMPLETED' || orderStatus === 'CANCELLED') return null
  if(dealStatus === 'REJECTED' || dealStatus === 'CANCELLED') return null

  if(dealStatus === 'AGREED' && !hasOrder){
    return {
      priority: 1,
      actionLabel: '주문 생성 필요',
      description: '주문을 생성해 거래를 이어가세요.'
    }
  }

  if(orderStatus === 'ACCEPTED'){
    return {
      priority: 2,
      actionLabel: '결제 필요',
      description: '결제 준비를 진행할 수 있습니다.'
    }
  }

  if(orderStatus === 'PENDING'){
    return {
      priority: 3,
      actionLabel: '주문 승인 대기',
      description: '주문 승인 처리를 기다리고 있습니다.'
    }
  }

  if(orderStatus === 'SHIPPED'){
    return {
      priority: 4,
      actionLabel: '거래 완료 처리 대기',
      description: '배송 완료 상태입니다. 거래 완료 처리 대기 중입니다.'
    }
  }

  if(dealStatus === 'NEGOTIATING'){
    return {
      priority: 5,
      actionLabel: '거래 승인 대기',
      description: '상대방의 거래 승인을 기다리고 있습니다.'
    }
  }

  return null
}

// format price for display (KRW)
function formatPrice(n){
  try{
    return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(n)
  }catch(e){
    return n
  }
}

export default function App(){
  const authenticationContext = resolveAuthenticationContext()
  const currentUserBootstrap = resolveCurrentUserBootstrapContext()
  const fallbackCurrentUser = currentUserBootstrap.fallbackUser
  const bootstrapUserId = currentUserBootstrap.userId
  const [, setAuthSessionVersion] = useState(0)
  const [activeView, setActiveView] = useState('market')
  const [bootstrapAccess, setBootstrapAccess] = useState(false)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginSubmitting, setLoginSubmitting] = useState(false)
  const [loginError, setLoginError] = useState(null)
  const [currentUser, setCurrentUser] = useState(fallbackCurrentUser)
  const [userLoading, setUserLoading] = useState(false)
  const [userError, setUserError] = useState(null)
  const [market, setMarket] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)

  // Deal form state
  const [quantity, setQuantity] = useState('')
  const [proposedPrice, setProposedPrice] = useState('')
  const [formErrors, setFormErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)

  // Created deal
  const [deal, setDeal] = useState(null)
  const [dealError, setDealError] = useState(null)
  const [statusUpdating, setStatusUpdating] = useState(false)
  const [statusMessage, setStatusMessage] = useState(null)

  // Order state for Step 16
  const [order, setOrder] = useState(null)
  const [orderCreating, setOrderCreating] = useState(false)
  const [orderStatusUpdating, setOrderStatusUpdating] = useState(false)
  const [orderMessage, setOrderMessage] = useState(null)
  const [orderError, setOrderError] = useState(null)

  // History state for Step 18
  const [historyItems, setHistoryItems] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState(null)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [historyScope, setHistoryScope] = useState('MY')
  const [historyFilter, setHistoryFilter] = useState('ALL')
  const [historySearch, setHistorySearch] = useState('')
  const [historySort, setHistorySort] = useState('CREATED_DESC')
  const [historyDetailDealId, setHistoryDetailDealId] = useState(null)
  const [historyActionProcessing, setHistoryActionProcessing] = useState(false)
  const [historyActionMessage, setHistoryActionMessage] = useState(null)
  const [historyActionError, setHistoryActionError] = useState(null)
  const [showAllActionItems, setShowAllActionItems] = useState(false)

  const activeUser = currentUser || fallbackCurrentUser
  const isSeller = isSellerRole(activeUser.role)
  const isAuthenticatedSession = authenticationContext.status === 'authenticated'
  const isAuthGateVisible = !isAuthenticatedSession && !bootstrapAccess
  const currentUserCode = labelUserCode(activeUser.role)
  const currentUserDisplay = `${currentUserCode} #${activeUser.id}`
  const actionCenterTitle = isSeller ? '판매자가 해야 할 일' : isBuyerRole(activeUser.role) ? '내가 해야 할 일' : '사용자 액션 센터'
  const actionCenterDesc = isSeller ? '지금 판매자가 확인해야 하는 거래' : isBuyerRole(activeUser.role) ? '지금 처리해야 하는 거래' : '현재 사용자 기준으로 확인이 필요한 거래'

  function resetAuthCaches(){
    AUTH_ME_CACHE.clear()
    AUTH_ME_PROMISE_CACHE.clear()
  }

  function clearAuthenticationSession(){
    clearAuthSessionStorage()
    resetAuthCaches()
  }

  async function revokeCurrentRefreshToken(){
    const accessToken = readAuthTokenFromStorage()
    const refreshToken = readRefreshTokenFromStorage()
    if(!accessToken || !refreshToken) return

    try{
      await fetch(buildAuthLogoutUrl(), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`
        },
        body: JSON.stringify({ refresh_token: refreshToken })
      })
    }catch(err){
      console.error('Logout revoke error', err)
    }
  }

  useEffect(()=>{
    setActiveView('market')
    setSelected(null)
    setDeal(null)
    setDealError(null)
    setStatusMessage(null)
    setOrder(null)
    setOrderError(null)
    setOrderMessage(null)
    setHistoryItems([])
    setHistoryLoaded(false)
    setHistoryError(null)
    setHistoryScope('MY')
    setHistoryFilter('ALL')
    setHistorySearch('')
    setHistorySort('CREATED_DESC')
    setHistoryDetailDealId(null)
    setHistoryActionMessage(null)
    setHistoryActionError(null)
    setShowAllActionItems(false)
  }, [bootstrapUserId, isAuthGateVisible])

  useEffect(()=>{
    if(isAuthGateVisible){
      setUserLoading(false)
      setUserError(null)
      return
    }

    let cancelled = false

    async function loadCurrentUser(){
      setUserLoading(true)
      setUserError(null)
      setCurrentUser(getFallbackCurrentUser(bootstrapUserId))
      try{
        const data = isAuthenticatedSession
          ? await fetchAuthenticatedCurrentUser(bootstrapUserId)
          : await fetchCurrentUserById(bootstrapUserId)
        if(cancelled) return

        setCurrentUser(data)
      }catch(err){
        console.error('Current user load error', err)
        if(cancelled) return
        if(isAuthenticatedSession && err?.status === 401){
          clearAuthenticationSession()
          setBootstrapAccess(false)
          setLoginError('로그인이 만료되었습니다. 다시 로그인해 주세요.')
          setCurrentUser(getFallbackCurrentUser(BOOTSTRAP_USER_ID))
          setAuthSessionVersion(v => v + 1)
          return
        }
        setUserError(getCurrentUserRuntimeErrorMessage(err))
      }finally{
        if(!cancelled) setUserLoading(false)
      }
    }

    loadCurrentUser()

    return ()=>{
      cancelled = true
    }
  }, [bootstrapUserId, isAuthGateVisible, isAuthenticatedSession])

  // Load market data
  useEffect(()=>{
    if(isAuthGateVisible){
      setLoading(false)
      setError(null)
      return
    }

    async function load(){
      setLoading(true); setError(null)
      try{
        const res = await fetch(API + '/market')
        if(!res.ok){
          const j = await res.json().catch(()=>({detail: res.statusText}))
          throw new Error(j.detail || 'Failed to load market')
        }
        const data = await res.json()
        setMarket(data)
      }catch(e){
        console.error('Market load error', e)
        setError('Market data를 불러오지 못했습니다.')
      }finally{ setLoading(false) }
    }
    load()
  }, [isAuthGateVisible])

  async function handleLoginSubmit(e){
    e.preventDefault()
    const email = loginEmail.trim()
    const password = loginPassword

    setLoginError(null)

    if(!email || !password){
      setLoginError('이메일과 비밀번호를 입력해 주세요.')
      return
    }

    setLoginSubmitting(true)
    try{
      const res = await fetch(buildAuthLoginUrl(), {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ email, password })
      })

      if(res.ok){
        const data = await res.json()
        storeAuthToken(data.access_token)
        storeRefreshToken(data.refresh_token)
        storeAuthenticatedUserId(data.user_id)
        resetAuthCaches()
        setBootstrapAccess(false)
        setLoginEmail('')
        setLoginPassword('')
        setCurrentUser(getFallbackCurrentUser(data.user_id))
        setUserError(null)
        setAuthSessionVersion(v => v + 1)
        return
      }

      const j = await res.json().catch(()=>({detail: res.statusText}))
      if(res.status === 401){
        setLoginError('이메일 또는 비밀번호를 확인해 주세요.')
      }else if(res.status === 400){
        setLoginError(j.detail || '이메일과 비밀번호를 입력해 주세요.')
      }else{
        setLoginError('로그인에 실패했습니다.')
      }
      console.error('Login error', res.status, j)
    }catch(err){
      console.error('Login network error', err)
      setLoginError('서버와 통신할 수 없습니다.')
    }finally{
      setLoginSubmitting(false)
    }
  }

  function handleContinueWithBootstrap(){
    clearAuthenticationSession()
    setBootstrapAccess(true)
    setLoginError(null)
    setLoginPassword('')
    setUserError(null)
    setAuthSessionVersion(v => v + 1)
  }

  function handleLogout(){
    Promise.resolve(revokeCurrentRefreshToken()).finally(()=>{
      clearAuthenticationSession()
      setBootstrapAccess(false)
      setLoginError(null)
      setLoginEmail('')
      setLoginPassword('')
      setCurrentUser(getFallbackCurrentUser(BOOTSTRAP_USER_ID))
      setUserError(null)
      setAuthSessionVersion(v => v + 1)
    })
  }

  // When selecting product, initialize form defaults
  useEffect(()=>{
    if(selected){
      setQuantity(String(selected.quantity || ''))
      setProposedPrice(String(selected.price || ''))
      setFormErrors({})
      setDeal(null)
      setOrder(null)
      setDealError(null)
      setOrderError(null)
      setOrderMessage(null)
    }
  }, [selected])

  function validate(){
    const err = {}
    const q = Number(quantity)
    const p = Number(proposedPrice)
    if(isNaN(q) || q <= 0) err.quantity = '거래 수량은 0보다 커야 합니다.'
    if(isNaN(p) || p <= 0) err.proposedPrice = '제안 가격은 0보다 커야 합니다.'
    setFormErrors(err)
    return Object.keys(err).length === 0
  }

  async function handleSubmit(e){
    e.preventDefault()
    setDealError(null)
    if(!selected){ setDealError('상품을 선택하세요.'); return }
    if(!validate()) return
    setSubmitting(true)
    try{
      const payload = {
        product_id: selected.product_id,
        buyer_id: activeUser.id,
        quantity: Number(quantity),
        proposed_price: Number(proposedPrice)
      }
      const res = await fetch(API + '/deals', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
      })
      if(res.ok){
        const d = await res.json()
        setDeal(d)
        setOrder(null)
        setOrderError(null)
        setOrderMessage(null)
        setSelected(null)
        setActiveView('dealRoom')
        alert('거래 제안이 등록되었습니다. Deal Room으로 이동합니다.')
      }else{
        const j = await res.json().catch(()=>({detail: res.statusText}))
        if(res.status === 404) setDealError('상품 또는 구매자를 찾을 수 없습니다.')
        else if(res.status === 400) setDealError(j.detail || '거래 제안을 등록할 수 없습니다.')
        else setDealError('서버와 통신할 수 없습니다.')
        console.error('Deal create error', res.status, j)
      }
    }catch(err){
      console.error('Network error', err)
      setDealError('서버와 통신할 수 없습니다.')
    }finally{ setSubmitting(false) }
  }

  async function refreshDeal(){
    if(!deal) return
    try{
      const res = await fetch(API + `/deals/${deal.id}`)
      if(res.ok){
        const d = await res.json()
        setDeal(d)
        setStatusMessage(null)
        setOrderError(null)
      }else{
        const j = await res.json().catch(()=>({detail: res.statusText}))
        setDealError(j.detail || 'Deal을 불러오지 못했습니다.')
      }
    }catch(e){
      console.error('refreshDeal error', e)
      setDealError('서버와 통신할 수 없습니다.')
    }
  }

  async function updateDealStatus(newStatus){
    if(!deal) return
    const confirmMsg = newStatus === 'AGREED'
      ? '거래를 승인하시겠습니까?'
      : newStatus === 'REJECTED'
        ? '이 거래 제안을 거절하시겠습니까?'
        : '이 거래를 취소하시겠습니까?'
    if(!confirm(confirmMsg)) return

    setDealError(null)
    setStatusMessage(null)
    setStatusUpdating(true)
    try{
      const res = await fetch(API + `/deals/${deal.id}/status`, {
        method: 'PATCH',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ status: newStatus })
      })
      if(res.ok){
        const d = await res.json()
        setDeal(d)
        setOrderError(null)
        const msg = newStatus === 'AGREED' ? '거래가 승인되었습니다.' : newStatus === 'REJECTED' ? '거래가 거절되었습니다.' : '거래가 취소되었습니다.'
        setStatusMessage(msg)
      }else{
        const j = await res.json().catch(()=>({detail: res.statusText}))
        if(res.status === 404) setDealError('Deal을 찾을 수 없습니다.')
        else if(res.status === 400) setDealError(j.detail || '상태 변경에 실패했습니다.')
        else setDealError('서버와 통신할 수 없습니다.')
        console.error('status update error', res.status, j)
      }
    }catch(err){
      console.error('Network error', err)
      setDealError('서버와 통신할 수 없습니다.')
    }finally{ setStatusUpdating(false) }
  }

  async function loadOrderForDeal(dealId){
    if(!dealId) return null
    setOrderError(null)
    try{
      const res = await fetch(API + `/deals/${dealId}/order`)
      if(res.ok){
        const data = await res.json()
        setOrder(data)
        return data
      }else if(res.status === 404){
        setOrder(null)
        return null
      }else{
        const j = await res.json().catch(()=>({detail: res.statusText}))
        setOrderError(j.detail || '주문을 불러오지 못했습니다.')
        return null
      }
    }catch(err){
      console.error('refreshOrder error', err)
      setOrderError('서버와 통신할 수 없습니다.')
      return null
    }
  }

  async function refreshOrder(){
    if(!deal) return
    setOrderMessage(null)
    await loadOrderForDeal(deal.id)
  }

  useEffect(()=>{
    if(!deal || !deal.id){
      setOrder(null)
      return
    }
    loadOrderForDeal(deal.id)
  }, [deal?.id, deal?.status])

  async function createOrderFromDeal(){
    if(!deal || orderCreating) return
    setOrderError(null)
    setOrderMessage(null)
    setOrderCreating(true)
    try{
      const res = await fetch(API + `/deals/${deal.id}/create-order`, { method: 'POST' })

      if(res.ok){
        const data = await res.json()
        setOrder(data)
        setOrderMessage('주문이 생성되었습니다.')
        return
      }

      const j = await res.json().catch(()=>({detail: res.statusText}))
      const detail = String(j.detail || '')

      if(res.status === 400 && /already/i.test(detail)){
        const existingOrder = await loadOrderForDeal(deal.id)
        if(existingOrder){
          setOrderMessage('이미 이 거래에 대한 주문이 생성되어 기존 주문을 표시합니다.')
          return
        }
        setOrderError('이미 이 거래에 대한 주문이 생성되었습니다.')
        return
      }

      if(res.status === 404){
        setOrderError(detail || 'Deal을 찾을 수 없습니다.')
        return
      }

      if(res.status === 400){
        setOrderError(detail || '주문 생성 요청이 올바르지 않습니다.')
        return
      }

      setOrderError(detail || '주문 생성에 실패했습니다.')
    }catch(err){
      console.error('createOrderFromDeal error', err)
      setOrderError('서버와 통신할 수 없습니다.')
    }finally{
      setOrderCreating(false)
    }
  }

  async function updateOrderStatus(){
    if(!order || orderStatusUpdating) return

    const action = ORDER_NEXT_ACTION[order.status]
    if(!action) return
    if(!confirm(action.confirmMessage)) return

    setOrderError(null)
    setOrderMessage(null)
    setOrderStatusUpdating(true)

    try{
      const res = await fetch(API + `/orders/${order.id}/status`, {
        method: 'PATCH',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ status: action.nextStatus })
      })

      if(res.ok){
        const data = await res.json()
        setOrder(data)
        setOrderMessage(action.successMessage)
        return
      }

      const j = await res.json().catch(()=>({detail: res.statusText}))
      if(res.status === 404){
        setOrderError('주문을 찾을 수 없습니다.')
      }else if(res.status === 400){
        setOrderError(j.detail || '주문 상태 변경에 실패했습니다.')
      }else{
        setOrderError('주문 상태를 변경하지 못했습니다.')
      }
      console.error('order status update error', res.status, j)
    }catch(err){
      console.error('updateOrderStatus network error', err)
      setOrderError('서버와 통신할 수 없습니다.')
    }finally{
      setOrderStatusUpdating(false)
    }
  }

  async function fetchHistoryOrderByDealId(dealId){
    try{
      const res = await fetch(API + `/deals/${dealId}/order`)
      if(res.ok) return await res.json()
      if(res.status === 404) return null
      const j = await res.json().catch(()=>({detail: res.statusText}))
      console.error('history order load error', dealId, res.status, j)
      return null
    }catch(err){
      console.error('history order network error', dealId, err)
      return null
    }
  }

  async function fetchHistoryCompletionByDealId(dealId){
    try{
      const res = await fetch(API + `/deals/${dealId}/completion`)
      if(res.ok) return await res.json()
      if(res.status === 404) return null
      const j = await res.json().catch(()=>({detail: res.statusText}))
      console.error('history completion load error', dealId, res.status, j)
      return null
    }catch(err){
      console.error('history completion network error', dealId, err)
      return null
    }
  }

  async function loadHistory(forceReload = false){
    if(historyLoading) return
    if(historyLoaded && !forceReload) return

    setHistoryLoading(true)
    setHistoryError(null)
    try{
      const dealsRes = await fetch(buildDealsUrl())
      if(!dealsRes.ok){
        const j = await dealsRes.json().catch(()=>({detail: dealsRes.statusText}))
        setHistoryError(getDealsLoadErrorMessage(dealsRes.status, j.detail))
        return
      }

      const deals = await dealsRes.json()
      if(!Array.isArray(deals)){
        setHistoryError('거래 조회 응답 형식이 올바르지 않습니다.')
        return
      }

      const joined = await Promise.all(
        deals.map(async (d) => {
          const canHaveOrder = d.status === 'AGREED'
          const orderData = canHaveOrder ? await fetchHistoryOrderByDealId(d.id) : null
          const completionData = orderData ? await fetchHistoryCompletionByDealId(d.id) : null

          const completed = Boolean(
            (completionData && completionData.completed === true) ||
            (orderData && orderData.status === 'COMPLETED')
          )

          return {
            deal: d,
            order: orderData,
            completion: completionData,
            completed
          }
        })
      )

      setHistoryItems(joined)
      setHistoryLoaded(true)
    }catch(err){
      console.error('history load network error', err)
      setHistoryError('서버와 통신할 수 없습니다.')
    }finally{
      setHistoryLoading(false)
    }
  }

  useEffect(()=>{
    if(activeView === 'history'){
      loadHistory(false)
    }
  }, [activeView])

  const scopedHistory = historyItems.filter(item => {
    if(historyScope === 'MY') return item.deal.buyer_id === activeUser.id
    return true
  })

  const myHistory = historyItems.filter(item => item.deal.buyer_id === activeUser.id)

  const searchedHistory = scopedHistory.filter(item => {
    const keyword = historySearch.trim()
    if(!keyword) return true
    const dealIdText = String(item.deal.id)
    const productIdText = String(item.deal.product_id)
    return dealIdText.includes(keyword) || productIdText.includes(keyword)
  })

  const statusFilteredHistory = searchedHistory.filter(item => {
    if(historyFilter === 'COMPLETED') return item.completed
    if(historyFilter === 'IN_PROGRESS') return !item.completed
    return true
  })

  const sortedHistory = [...statusFilteredHistory].sort((a, b) => {
    if(historySort === 'CREATED_ASC'){
      return new Date(a.deal.created_at).getTime() - new Date(b.deal.created_at).getTime()
    }
    if(historySort === 'PRICE_DESC'){
      return Number(b.deal.proposed_price) - Number(a.deal.proposed_price)
    }
    if(historySort === 'PRICE_ASC'){
      return Number(a.deal.proposed_price) - Number(b.deal.proposed_price)
    }
    return new Date(b.deal.created_at).getTime() - new Date(a.deal.created_at).getTime()
  })

  const actionRequiredQueue = myHistory
    .map(item => {
      const queueInfo = getActionQueueItem(item)
      if(!queueInfo) return null
      return {
        ...queueInfo,
        item,
        createdAtTime: new Date(item.deal.created_at).getTime() || 0
      }
    })
    .filter(Boolean)
    .sort((a, b) => {
      if(a.priority !== b.priority) return a.priority - b.priority
      return b.createdAtTime - a.createdAtTime
    })

  const actionRequiredItems = showAllActionItems ? actionRequiredQueue : actionRequiredQueue.slice(0, 5)
  const hasMoreActionItems = actionRequiredQueue.length > 5

  const actionRequiredErrorMessage = historyError
    ? (historyError.includes('서버와 통신') ? '서버와 통신할 수 없습니다.' : '처리할 거래를 불러오지 못했습니다.')
    : null

  const historyDashboard = {
    total: historyItems.length,
    completed: myHistory.filter(item => item.completed).length,
    inProgress: myHistory.filter(item => !item.completed).length,
    noOrder: myHistory.filter(item => !item.order).length,
    actionRequired: actionRequiredQueue.length
  }

  const selectedHistoryDetail = historyItems.find(item => item.deal.id === historyDetailDealId) || null
  const selectedHistoryAction = selectedHistoryDetail ? getActionState(selectedHistoryDetail) : null

  async function handleCreateOrderFromHistory(item){
    if(!item || historyActionProcessing) return

    setHistoryActionError(null)
    setHistoryActionMessage(null)
    setHistoryActionProcessing(true)

    try{
      const res = await fetch(API + `/deals/${item.deal.id}/create-order`, { method: 'POST' })
      if(res.ok){
        setHistoryActionMessage('주문이 생성되었습니다.')
        await loadHistory(true)
        return
      }

      const j = await res.json().catch(()=>({detail: res.statusText}))
      const detail = String(j.detail || '')

      if(res.status === 400 && /already/i.test(detail)){
        setHistoryActionMessage('이미 주문이 생성되어 최신 정보를 다시 불러왔습니다.')
        await loadHistory(true)
        return
      }

      if(res.status === 404){
        setHistoryActionError('거래를 찾을 수 없습니다.')
      }else if(res.status === 400){
        setHistoryActionError(detail || '주문 생성에 실패했습니다.')
      }else{
        setHistoryActionError('주문을 생성하지 못했습니다.')
      }
      console.error('history create order error', res.status, j)
    }catch(err){
      console.error('history create order network error', err)
      setHistoryActionError('서버와 통신할 수 없습니다.')
    }finally{
      setHistoryActionProcessing(false)
    }
  }

  function handlePaymentPrepare(){
    setHistoryActionError(null)
    setHistoryActionMessage('결제 기능은 다음 단계에서 연결됩니다.')
  }

  function openHistoryDetail(dealId){
    setHistoryDetailDealId(dealId)
    setHistoryActionMessage(null)
    setHistoryActionError(null)
  }

  if(isAuthGateVisible){
    return (
      <div className="page login-page">
        <main className="login-shell">
          <section className="login-panel card">
            <div className="brand login-brand">NME</div>
            <h1 className="login-title">Non-ferrous Metals Exchange</h1>
            <p className="login-subtitle">기존 사용자 계정으로 로그인해 현재 사용자와 거래 화면을 연결합니다.</p>

            <form className="login-form" onSubmit={handleLoginSubmit}>
              <div className="form-row">
                <label>Email</label>
                <input type="email" value={loginEmail} onChange={e=> setLoginEmail(e.target.value)} autoComplete="username" />
              </div>

              <div className="form-row">
                <label>Password</label>
                <input type="password" value={loginPassword} onChange={e=> setLoginPassword(e.target.value)} autoComplete="current-password" />
              </div>

              <div className="form-actions login-actions">
                <button type="submit" disabled={loginSubmitting}>{loginSubmitting ? '로그인 중...' : '로그인'}</button>
                <button type="button" className="secondary" onClick={handleContinueWithBootstrap} disabled={loginSubmitting}>개발용 기본 사용자로 계속</button>
              </div>
            </form>

            {loginError && <div className="error-msg">{loginError}</div>}

            <div className="login-help">
              <div>테스트 계정</div>
              <div>Buyer: bob@example.com / secret</div>
              <div>Seller: charlie@example.com / secret</div>
            </div>
          </section>
        </main>

        <footer className="footer">© NME</footer>
      </div>
    )
  }

  return (
    <div className="page">
      <header className="header">
        <div className="brand">NME</div>
        <div className="header-actions">
          <nav>
            <button className={`navbtn ${activeView === 'market' ? 'active' : ''}`} onClick={()=> setActiveView('market')}>Market</button>
            <button className={`navbtn ${activeView === 'dealRoom' ? 'active' : ''}`} onClick={()=> setActiveView('dealRoom')}>거래 관리</button>
            <button className={`navbtn ${activeView === 'history' ? 'active' : ''}`} onClick={()=> setActiveView('history')}>거래 이력</button>
          </nav>
          <button className="secondary" onClick={handleLogout}>{isAuthenticatedSession ? '로그아웃' : '로그인 화면'}</button>
        </div>
      </header>

      <main>
        <section className="hero">
          <h1>NME Live Market</h1>
          <p className="subtitle">Real-time Non-Ferrous Metals Marketplace</p>
        </section>

        {userLoading && <div className="info">현재 사용자 정보를 불러오는 중...</div>}
        {userError && <div className="error-msg">{userError}</div>}

        <section>
          {activeView === 'market' && (
            <>
          <div className="proposal" style={{paddingTop:0}}>
            <div className="history-user">현재 사용자: {currentUserDisplay} · {activeUser.name} · 역할: {labelUserRole(activeUser.role)}</div>
          </div>
          {loading && <div className="info">Loading market data...</div>}
          {error && <div className="error">{error}</div>}
          {!loading && !error && market.length === 0 && <div className="info">No products available.</div>}

          <div className="grid">
            {market.map(p => (
              <article className="card" key={p.product_id}>
                <div className="card-head">
                  <div className="metal">{p.metal}</div>
                  <div className="grade">Grade: {p.grade}</div>
                </div>
                <div className="card-body">
                  <div>Product ID: <strong>{p.product_id}</strong></div>
                  <div>Quantity: <strong>{p.quantity} {p.unit}</strong></div>
                  <div>Price: <strong>{formatPrice(p.price)}</strong></div>
                  <div>Status: <strong>{p.status}</strong></div>
                </div>
                <div className="card-foot">
                  <button onClick={()=> setSelected(p)}>거래 제안</button>
                </div>
              </article>
            ))}
          </div>

          <div className="proposal">
            {selected ? (
              <form className="card deal-form" onSubmit={handleSubmit}>
                <h3>거래 제안</h3>
                <div>Product: <strong>{selected.metal} {selected.grade}</strong></div>
                <div>Product ID: <strong>{selected.product_id}</strong></div>

                <div className="form-row">
                  <label>거래 수량</label>
                  <input type="number" value={quantity} onChange={e=> setQuantity(e.target.value)} />
                  {formErrors.quantity && <div className="error-msg">{formErrors.quantity}</div>}
                </div>

                <div className="form-row">
                  <label>제안 가격</label>
                  <input type="number" value={proposedPrice} onChange={e=> setProposedPrice(e.target.value)} />
                  {formErrors.proposedPrice && <div className="error-msg">{formErrors.proposedPrice}</div>}
                </div>

                <div className="form-actions">
                  <button type="submit" disabled={submitting}>{submitting? '거래 제안 보내는 중...':'거래 제안 보내기'}</button>
                  <button type="button" className="secondary" onClick={()=> setSelected(null)} disabled={submitting}>취소</button>
                </div>
                {dealError && <div className="error-msg">{dealError}</div>}
              </form>
            ) : (
              <div className="muted">상품을 선택하면 거래 제안 준비 영역이 표시됩니다.</div>
            )}
          </div>
          </>
          )}

          {activeView === 'dealRoom' && (
            <div className="proposal">
              {deal ? (
              <div className="card deal-room">
                <h3>Deal Room</h3>
                <div className="history-user" style={{marginTop:0}}>현재 사용자: {currentUserDisplay} · {activeUser.name} · 역할: {labelUserRole(activeUser.role)}</div>
                <div className="deal-row"><strong>Deal #{deal.id}</strong></div>
                <div>Product: #{deal.product_id}</div>
                <div>Buyer: #{deal.buyer_id}</div>
                <div>Quantity: {deal.quantity} {deal.unit || ''}</div>
                <div>Proposed Price: <strong>{formatPrice(deal.proposed_price)}</strong></div>
                <div>Deal Status: <span className="status-badge">{deal.status}</span></div>
                <div>Created: <strong>{deal.created_at}</strong></div>

                {statusMessage && <div className="success-msg">{statusMessage}</div>}

                <div style={{marginTop:12}}>
                  <button onClick={refreshDeal} disabled={statusUpdating}>상태 새로고침</button>
                </div>

                {deal.status === 'NEGOTIATING' && (
                  <div className="form-actions" style={{marginTop:12}}>
                    <button onClick={()=> updateDealStatus('AGREED')} disabled={statusUpdating}>{statusUpdating? '처리 중...':'거래 승인'}</button>
                    <button className="secondary" onClick={()=> updateDealStatus('REJECTED')} disabled={statusUpdating}>{statusUpdating? '처리 중...':'거래 거절'}</button>
                    <button className="secondary" onClick={()=> updateDealStatus('CANCELLED')} disabled={statusUpdating}>{statusUpdating? '처리 중...':'거래 취소'}</button>
                  </div>
                )}

                {deal.status === 'AGREED' && (
                  <div className="order-panel">
                    <h4>Order</h4>
                    <div>거래가 승인되었습니다.</div>
                    <div>이 Deal을 주문으로 생성할 수 있습니다.</div>

                    {!order ? (
                      <>
                        <div className="muted" style={{padding:0, marginTop:8}}>아직 주문이 생성되지 않았습니다.</div>
                        <div className="form-actions" style={{marginTop:12}}>
                          <button onClick={createOrderFromDeal} disabled={orderCreating}>{orderCreating ? '주문 생성 중...' : '주문 생성'}</button>
                          <button className="secondary" onClick={refreshOrder} disabled={orderCreating}>주문 새로고침</button>
                        </div>
                        {orderMessage && <div className="success-msg">{orderMessage}</div>}
                        {orderError && <div className="error-msg">{orderError}</div>}
                      </>
                    ) : (
                      <div className="order-room">
                        <h4>Order #{order.id}</h4>
                        <div>Deal ID: <strong>#{deal.id}</strong></div>
                        <div>Product ID: <strong>#{order.product_id}</strong></div>
                        <div>Buyer ID: <strong>#{order.buyer_id}</strong></div>
                        <div>Quantity: <strong>{order.quantity}</strong></div>
                        <div>Price: <strong>{formatPrice(order.price)}</strong></div>
                        <div>Order Status: <span className={`status-badge ${getStatusClass(order.status)}`}>{order.status}</span></div>
                        <div>Created At: <strong>{order.created_at}</strong></div>
                        <div style={{marginTop:8}}>현재 상태: <strong>{order.status}</strong></div>

                        <div className="order-progress" style={{marginTop:12}}>
                          {ORDER_PROGRESS.map(step => {
                            const done = isProgressDone(order.status, step.status)
                            const current = order.status === step.status
                            return (
                              <div key={step.status} className={`progress-step ${done ? 'done' : ''} ${current ? 'current' : ''}`}>
                                {step.label}
                              </div>
                            )
                          })}
                        </div>

                        <div className="form-actions" style={{marginTop:12}}>
                          <button className="secondary" onClick={refreshOrder} disabled={orderStatusUpdating || orderCreating}>주문 상태 새로고침</button>
                          {ORDER_NEXT_ACTION[order.status] && (
                            <button onClick={updateOrderStatus} disabled={orderStatusUpdating || orderCreating}>
                              {orderStatusUpdating ? '처리 중...' : ORDER_NEXT_ACTION[order.status].buttonLabel}
                            </button>
                          )}
                        </div>

                        {order.status === 'COMPLETED' && (
                          <div className="success-msg">거래가 완료되었습니다.</div>
                        )}

                        {order.status === 'CANCELLED' && (
                          <div className="error-msg">주문이 취소되어 다음 단계를 진행할 수 없습니다.</div>
                        )}

                        {orderMessage && <div className="success-msg">{orderMessage}</div>}
                        {orderError && <div className="error-msg">{orderError}</div>}
                      </div>
                    )}
                  </div>
                )}

                {deal.status === 'REJECTED' && <div className="error-msg">거래 제안이 거절되었습니다.</div>}
                {deal.status === 'CANCELLED' && <div className="error-msg">거래가 취소되었습니다.</div>}

                {dealError && <div className="error-msg">{dealError}</div>}
              </div>
            ) : (
              <div className="muted">아직 Deal Room에 표시할 거래가 없습니다. Market에서 거래를 제안해 주세요.</div>
            )}
            </div>
          )}

          {activeView === 'history' && (
            <div className="proposal history-section">
              <div className="history-head">
                <h3>거래 이력</h3>
                <button className="secondary" onClick={()=> loadHistory(true)} disabled={historyLoading}>
                  {historyLoading ? '불러오는 중...' : '이력 새로고침'}
                </button>
              </div>

              <div className="history-user">내 거래 관리 · 현재 사용자: {currentUserDisplay} · {activeUser.name} · 역할: {labelUserRole(activeUser.role)}</div>

              <div className="dashboard-grid">
                <article className="card dashboard-card">
                  <div className="dashboard-title">전체 거래</div>
                  <div className="dashboard-value">{historyDashboard.total}건</div>
                </article>
                <article className="card dashboard-card">
                  <div className="dashboard-title">진행중</div>
                  <div className="dashboard-value">{historyDashboard.inProgress}건</div>
                </article>
                <article className="card dashboard-card">
                  <div className="dashboard-title">완료</div>
                  <div className="dashboard-value">{historyDashboard.completed}건</div>
                </article>
                <article className="card dashboard-card">
                  <div className="dashboard-title">주문 생성 전</div>
                  <div className="dashboard-value">{historyDashboard.noOrder}건</div>
                </article>
                <article className="card dashboard-card">
                  <div className="dashboard-title">{actionCenterTitle}</div>
                  <div className="dashboard-value">{historyDashboard.actionRequired}건</div>
                  <div className="dashboard-sub">{actionCenterDesc}</div>
                </article>
              </div>

              <div className="card action-required-panel">
                <div className="action-required-head">
                  <h4>{actionCenterTitle}</h4>
                  <span className="action-required-count">우선 처리 {historyDashboard.actionRequired}건</span>
                </div>

                {historyLoading && <div className="info">처리할 거래를 불러오는 중...</div>}
                {!historyLoading && actionRequiredErrorMessage && <div className="error-msg">{actionRequiredErrorMessage}</div>}

                {!historyLoading && !actionRequiredErrorMessage && actionRequiredQueue.length === 0 && (
                  <div className="action-required-empty">
                    <div>현재 처리할 거래가 없습니다.</div>
                    <div className="muted">새로운 거래가 제안되거나 진행되면 이곳에 표시됩니다.</div>
                  </div>
                )}

                {!historyLoading && !actionRequiredErrorMessage && actionRequiredItems.length > 0 && (
                  <div className="action-required-list">
                    {actionRequiredItems.map(({ item, actionLabel, description, priority }) => (
                      <article className="action-required-item" key={`action-${item.deal.id}`}>
                        <div className="action-required-top">
                          <strong>Deal #{item.deal.id}</strong>
                          <span className="priority-chip">우선순위 {priority}</span>
                        </div>
                        <div>Product ID: <strong>#{item.deal.product_id}</strong></div>
                        <div>수량: <strong>{item.deal.quantity}</strong></div>
                        <div>제안 가격: <strong>{formatPrice(item.deal.proposed_price)}</strong></div>
                        <div>현재 상태: <strong>{item.order ? labelOrderStatus(item.order.status) : labelDealStatus(item.deal.status)}</strong></div>
                        <div>{isSeller ? '판매자가 해야 할 일' : '내가 해야 할 일'}: <strong>{actionLabel}</strong></div>
                        <div className="action-required-desc">{description}</div>
                        <div className="action-required-meta">생성일: {formatDateTime(item.deal.created_at)}</div>
                        <div className="form-actions" style={{marginTop:10}}>
                          <button onClick={()=> openHistoryDetail(item.deal.id)}>거래 상세 보기</button>
                        </div>
                      </article>
                    ))}
                  </div>
                )}

                {!historyLoading && !actionRequiredErrorMessage && hasMoreActionItems && (
                  <div className="form-actions" style={{marginTop:10}}>
                    <button className="secondary" onClick={()=> setShowAllActionItems(v => !v)}>
                      {showAllActionItems ? '접기' : '전체 보기'}
                    </button>
                  </div>
                )}
              </div>

              <div className="history-filters">
                <button className={`filter-btn ${historyScope === 'MY' ? 'active' : ''}`} onClick={()=> setHistoryScope('MY')} disabled={historyLoading}>내 거래</button>
                <button className={`filter-btn ${historyScope === 'ALL' ? 'active' : ''}`} onClick={()=> setHistoryScope('ALL')} disabled={historyLoading}>전체 거래</button>
              </div>

              <div className="history-filters">
                <button className={`filter-btn ${historyFilter === 'ALL' ? 'active' : ''}`} onClick={()=> setHistoryFilter('ALL')} disabled={historyLoading}>전체</button>
                <button className={`filter-btn ${historyFilter === 'IN_PROGRESS' ? 'active' : ''}`} onClick={()=> setHistoryFilter('IN_PROGRESS')} disabled={historyLoading}>진행중</button>
                <button className={`filter-btn ${historyFilter === 'COMPLETED' ? 'active' : ''}`} onClick={()=> setHistoryFilter('COMPLETED')} disabled={historyLoading}>완료</button>
              </div>

              <div className="history-tools">
                <input
                  className="history-search"
                  placeholder="Deal ID / Product ID 검색"
                  value={historySearch}
                  onChange={e=> setHistorySearch(e.target.value)}
                  disabled={historyLoading}
                />
                {historySearch && (
                  <button className="secondary" onClick={()=> setHistorySearch('')} disabled={historyLoading}>검색 초기화</button>
                )}
                <select className="history-sort" value={historySort} onChange={e=> setHistorySort(e.target.value)} disabled={historyLoading}>
                  <option value="CREATED_DESC">최신순</option>
                  <option value="CREATED_ASC">오래된순</option>
                  <option value="PRICE_DESC">가격 높은순</option>
                  <option value="PRICE_ASC">가격 낮은순</option>
                </select>
              </div>

              {historyLoading && <div className="info">거래 정보를 불러오는 중...</div>}
              {historyError && <div className="error-msg">{historyError}</div>}

              {!historyLoading && !historyError && !historyDetailDealId && (
                <div className="history-count">총 {sortedHistory.length}건</div>
              )}

              {!historyLoading && !historyError && historyDetailDealId && selectedHistoryDetail && (
                <div className="card history-detail">
                  <h4>Deal #{selectedHistoryDetail.deal.id} 상세</h4>
                  <div className="detail-section">
                    <h5>거래 정보</h5>
                    <div>Deal ID: <strong>#{selectedHistoryDetail.deal.id}</strong></div>
                    <div>Product ID: <strong>#{selectedHistoryDetail.deal.product_id}</strong></div>
                    <div>Buyer ID: <strong>#{selectedHistoryDetail.deal.buyer_id}</strong></div>
                    <div>현재 사용자 역할: <strong>{labelUserRole(activeUser.role)}</strong></div>
                    <div>거래 구분: <strong>{selectedHistoryDetail.deal.buyer_id === activeUser.id ? '내 거래' : '전체 거래'}</strong></div>
                    <div>거래 수량: <strong>{selectedHistoryDetail.deal.quantity}</strong></div>
                    <div>제안 가격: <strong>{formatPrice(selectedHistoryDetail.deal.proposed_price)}</strong></div>
                    <div>거래 상태: <strong>{labelDealStatus(selectedHistoryDetail.deal.status)}</strong></div>
                    <div>생성일: <strong>{formatDateTime(selectedHistoryDetail.deal.created_at)}</strong></div>
                  </div>

                  <div className="detail-section">
                    <h5>주문 정보</h5>
                    <div>Order ID: <strong>{selectedHistoryDetail.order ? `#${selectedHistoryDetail.order.id}` : '없음'}</strong></div>
                    <div>주문 상태: <strong>{selectedHistoryDetail.order ? labelOrderStatus(selectedHistoryDetail.order.status) : '주문 생성 전'}</strong></div>
                    <div>주문 생성일: <strong>{formatDateTime(selectedHistoryDetail.order?.created_at)}</strong></div>
                    <div>주문 수량: <strong>{selectedHistoryDetail.order ? selectedHistoryDetail.order.quantity : '-'}</strong></div>
                    <div>주문 가격: <strong>{selectedHistoryDetail.order ? formatPrice(selectedHistoryDetail.order.price) : '-'}</strong></div>
                  </div>

                  <div className="detail-section">
                    <h5>거래 완료</h5>
                    <div>완료 여부: <strong>{selectedHistoryDetail.completed ? 'YES' : 'NO'}</strong></div>
                    <div>완료 상태: <strong>{selectedHistoryDetail.completed ? '거래 완료' : '진행 중'}</strong></div>
                    {selectedHistoryDetail.order?.status === 'CANCELLED' && (
                      <div className="action-helper">이 거래는 취소되어 더 이상 진행되지 않습니다.</div>
                    )}
                  </div>

                  <div className={`detail-section todo-box tone-${selectedHistoryAction?.tone || 'waiting'}`}>
                    <h5>현재 할 일</h5>
                    <div className="action-title">{selectedHistoryAction?.title}</div>
                    <div>{selectedHistoryAction?.description}</div>
                    <div style={{marginTop:8}}>현재 단계: <strong>{selectedHistoryAction?.currentStep}</strong></div>
                    <div>다음 단계: <strong>{selectedHistoryAction?.nextStep}</strong></div>
                    {selectedHistoryAction?.helper && <div className="action-helper">{selectedHistoryAction.helper}</div>}

                    <div className="form-actions" style={{marginTop:10}}>
                      {selectedHistoryAction?.actionType === 'create-order' && (
                        <button onClick={()=> handleCreateOrderFromHistory(selectedHistoryDetail)} disabled={historyActionProcessing}>
                          {historyActionProcessing ? '주문 생성 중...' : '주문 생성'}
                        </button>
                      )}
                      {selectedHistoryAction?.actionType === 'payment-ready' && (
                        <button onClick={handlePaymentPrepare} disabled={historyActionProcessing}>결제 준비</button>
                      )}
                    </div>

                    {historyActionMessage && <div className="success-msg">{historyActionMessage}</div>}
                    {historyActionError && <div className="error-msg">{historyActionError}</div>}
                  </div>

                  <div className="detail-section">
                    <h5>거래 진행 단계</h5>
                    <div className="detail-progress" style={{marginTop:8}}>
                      {buildTradeFlowSteps(selectedHistoryDetail).map(step => (
                        <div key={step.key} className={step.state}>
                          <span className="step-symbol">{step.state === 'done' ? '✓' : step.state === 'current' ? '●' : '○'}</span>
                          {step.label}
                        </div>
                      ))}
                    </div>
                    {getFlowTerminalNote(selectedHistoryDetail) && (
                      <div className="progress-terminal-note">{getFlowTerminalNote(selectedHistoryDetail)}</div>
                    )}
                  </div>

                  <div className="form-actions" style={{marginTop:12}}>
                    <button className="secondary" onClick={()=> { setHistoryDetailDealId(null); setHistoryActionMessage(null); setHistoryActionError(null) }}>뒤로가기</button>
                  </div>
                </div>
              )}

              {!historyLoading && !historyError && !historyDetailDealId && scopedHistory.length === 0 && (
                <div className="muted">아직 거래 내역이 없습니다.</div>
              )}

              {!historyLoading && !historyError && !historyDetailDealId && scopedHistory.length > 0 && sortedHistory.length === 0 && (
                <div className="muted">조건에 맞는 거래가 없습니다.</div>
              )}

              {!historyLoading && !historyError && !historyDetailDealId && sortedHistory.length > 0 && (
                <div className="history-grid">
                  {sortedHistory.map(item => {
                    const actionState = getActionState(item)
                    const summary = item.completed
                      ? '거래 완료'
                      : item.order?.status === 'CANCELLED'
                        ? '거래 취소'
                        : item.order
                          ? '진행 중'
                          : '주문 생성 전'
                    return (
                    <article className="card history-card" key={item.deal.id}>
                      <div className="history-title">Deal #{item.deal.id}</div>
                      <div>Product ID: <strong>#{item.deal.product_id}</strong></div>
                      <div>Buyer ID: <strong>#{item.deal.buyer_id}</strong></div>
                      <div>Quantity: <strong>{item.deal.quantity}</strong></div>
                      <div>Proposed Price: <strong>{formatPrice(item.deal.proposed_price)}</strong></div>
                      <div>Deal Status: <span className={`status-badge ${getStatusClass(item.deal.status)}`}>{labelDealStatus(item.deal.status)}</span></div>
                      <div>Order ID: <strong>{item.order ? `#${item.order.id}` : '없음'}</strong></div>
                      <div>Order Status: <span className={`status-badge ${getStatusClass(item.order?.status || 'noorder')}`}>{item.order ? labelOrderStatus(item.order.status) : '주문 생성 전'}</span></div>
                      <div>Created At: <strong>{formatDateTime(item.deal.created_at)}</strong></div>
                      <div>거래 상태 요약: <strong>{summary}</strong></div>
                      <div>현재 단계: <strong>{actionState.shortStatus}</strong></div>
                      <div>다음 행동: <strong>{actionState.nextStep}</strong></div>
                      <div className="form-actions" style={{marginTop:12}}>
                        <button onClick={()=> openHistoryDetail(item.deal.id)}>상세 보기</button>
                      </div>
                    </article>
                  )})}
                </div>
              )}
            </div>
          )}

        </section>
      </main>

      <footer className="footer">© NME</footer>
    </div>
  )
}
