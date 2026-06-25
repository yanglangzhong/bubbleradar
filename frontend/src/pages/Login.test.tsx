import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@/test/test-utils'
import Login from './Login'
import * as api from '@/services/api'
import * as store from '@/store'

vi.mock('@/services/api', async () => {
  const actual = await vi.importActual<typeof import('@/services/api')>('@/services/api')
  return {
    ...actual,
    authApi: {
      login: vi.fn(),
      getMe: vi.fn(),
    },
  }
})

describe('Login', () => {
  const setAuthSpy = vi.fn()

  beforeEach(() => {
    vi.spyOn(store.useAppStore.getState(), 'setAuth').mockImplementation(setAuthSpy)
    store.useAppStore.setState({
      auth: { user: null, token: null, isAuthenticated: false },
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders login form', () => {
    render(<Login />)

    expect(screen.getByText('登录 BubbleRadar')).toBeInTheDocument()
    expect(screen.getByLabelText('邮箱')).toBeInTheDocument()
    expect(screen.getByLabelText('密码')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '登录' })).toBeInTheDocument()
  })

  it('submits credentials and redirects on success', async () => {
    const loginMock = vi.spyOn(api.authApi, 'login').mockResolvedValue({
      access_token: 'test-token',
      token_type: 'bearer',
    })
    vi.spyOn(api.authApi, 'getMe').mockResolvedValue({
      id: 1,
      email: 'admin@example.com',
      is_active: true,
      is_superuser: true,
    })

    render(<Login />)

    await userEvent.type(screen.getByLabelText('邮箱'), 'admin@example.com')
    await userEvent.type(screen.getByLabelText('密码'), 'admin')
    await userEvent.click(screen.getByRole('button', { name: '登录' }))

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith({ username: 'admin@example.com', password: 'admin' })
    })

    await waitFor(() => {
      expect(setAuthSpy).toHaveBeenCalledWith('test-token', {
        id: 1,
        email: 'admin@example.com',
        is_active: true,
        is_superuser: true,
      })
    })
  })

  it('displays error message on failed login', async () => {
    vi.spyOn(api.authApi, 'login').mockRejectedValue({
      response: { data: { detail: 'Invalid credentials' } },
    })

    render(<Login />)

    await userEvent.type(screen.getByLabelText('邮箱'), 'bad@example.com')
    await userEvent.type(screen.getByLabelText('密码'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: '登录' }))

    await waitFor(() => {
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
    })
  })

  it('shows loading state while logging in', async () => {
    vi.spyOn(api.authApi, 'login').mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ access_token: 't', token_type: 'bearer' }), 100))
    )
    vi.spyOn(api.authApi, 'getMe').mockResolvedValue({
      id: 1,
      email: 'admin@example.com',
      is_active: true,
      is_superuser: true,
    })

    render(<Login />)

    await userEvent.type(screen.getByLabelText('邮箱'), 'admin@example.com')
    await userEvent.type(screen.getByLabelText('密码'), 'admin')
    await userEvent.click(screen.getByRole('button', { name: '登录' }))

    expect(screen.getByText('登录中…')).toBeInTheDocument()
  })
})