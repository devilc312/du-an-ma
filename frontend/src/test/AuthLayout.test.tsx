import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthLayout } from '../layouts/AuthLayout'
describe('AuthLayout', () => { it('renders a labelled Todo AI shell', () => { render(<MemoryRouter><AuthLayout><h1>Đăng nhập</h1></AuthLayout></MemoryRouter>); expect(screen.getAllByText('Todo AI')).toHaveLength(2); expect(screen.getByRole('heading', { name: 'Đăng nhập' })).toBeInTheDocument() }) })
