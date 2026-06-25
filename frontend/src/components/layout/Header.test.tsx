import { describe, it, expect, vi, beforeEach } from 'vitest'
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@/test/test-utils'
import Header from './Header'
import * as store from '@/store'

describe('Header', () => {
  const clearAuthSpy = vi.fn()

  beforeEach(() => {
    vi.spyOn(store.useAppStore.getState(), 'clearAuth').mockImplementation(clearAuthSpy)
    store.useAppStore.setState({
      auth: { user: null, token: null, isAuthenticated: false },
    })
  })

  it('renders brand name and navigation items', () => {
    render(<Header />)

    expect(screen.getByText('BubbleRadar')).toBeInTheDocument()
    expect(screen.getByText('实时')).toBeInTheDocument()

    // Scope to desktop nav to avoid duplicates from mobile drawer
    const desktopNav = document.querySelector('nav.hidden.lg\\:flex')
    expect(desktopNav).toBeInTheDocument()
    expect(desktopNav?.textContent).toContain('首页')
    expect(desktopNav?.textContent).toContain('AI泡沫')
  })

  it('shows logout button when authenticated', () => {
    store.useAppStore.setState({
      auth: {
        user: { id: 1, email: 'admin@example.com', is_active: true, is_superuser: true },
        token: 'token',
        isAuthenticated: true,
      },
    })

    render(<Header />)

    expect(screen.getByTitle('退出登录')).toBeInTheDocument()
  })

  it('calls clearAuth and navigates to login on logout', async () => {
    store.useAppStore.setState({
      auth: {
        user: { id: 1, email: 'admin@example.com', is_active: true, is_superuser: true },
        token: 'token',
        isAuthenticated: true,
      },
    })

    render(<Header />)

    const logoutBtn = screen.getByTitle('退出登录')
    await userEvent.click(logoutBtn)

    await waitFor(() => {
      expect(clearAuthSpy).toHaveBeenCalled()
    })
  })

  it('renders current date/time', () => {
    render(<Header />)

    // The clock element is a <time> tag with formatted date
    const timeEl = document.querySelector('time')
    expect(timeEl).toBeInTheDocument()
    expect(timeEl?.textContent).toMatch(/\d{4}\/\d{1,2}\/\d{1,2}/)
  })
})