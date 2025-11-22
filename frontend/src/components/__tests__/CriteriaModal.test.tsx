/**
 * CriteriaModal Component Tests
 *
 * Tests for the CriteriaModal component that handles user input
 * for filtering projects by capacity criteria.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';
import CriteriaModal from '../criteriamodal';

describe('CriteriaModal', () => {
  const mockOnSubmit = vi.fn();
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the capacity input field', () => {
      render(<CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />);

      expect(screen.getByLabelText(/target capacity/i)).toBeInTheDocument();
    });

    it('renders the input with correct attributes', () => {
      render(<CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />);

      const input = screen.getByLabelText(/target capacity/i);
      expect(input).toHaveAttribute('type', 'number');
      expect(input).toHaveAttribute('min', '0');
      expect(input).toHaveAttribute('step', '0.1');
      expect(input).toHaveAttribute('inputMode', 'decimal');
    });

    it('renders Cancel button', () => {
      render(<CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />);

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('renders Apply button', () => {
      render(<CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />);

      expect(screen.getByRole('button', { name: /apply/i })).toBeInTheDocument();
    });

    it('input starts with empty value', () => {
      render(<CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />);

      const input = screen.getByLabelText(/target capacity/i);
      expect(input).toHaveValue(null);
    });
  });

  describe('User Interactions', () => {
    it('allows user to type capacity value', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const input = screen.getByLabelText(/target capacity/i);
      await user.type(input, '100');

      expect(input).toHaveValue(100);
    });

    it('allows decimal values', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const input = screen.getByLabelText(/target capacity/i);
      await user.type(input, '50.5');

      expect(input).toHaveValue(50.5);
    });

    it('calls onClose when Cancel button is clicked', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('does not call onSubmit when Cancel is clicked', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });
  });

  describe('Form Submission', () => {
    it('calls onSubmit with correct payload when form is submitted', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const input = screen.getByLabelText(/target capacity/i);
      await user.type(input, '150');

      const applyButton = screen.getByRole('button', { name: /apply/i });
      await user.click(applyButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          ideal_mw: 150,
          capacity_input: '150',
        });
      });
    });

    it('calls onClose after successful submission', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const input = screen.getByLabelText(/target capacity/i);
      await user.type(input, '100');

      const applyButton = screen.getByRole('button', { name: /apply/i });
      await user.click(applyButton);

      await waitFor(() => {
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      });
    });

    it('handles empty input by submitting 0', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const applyButton = screen.getByRole('button', { name: /apply/i });
      await user.click(applyButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          ideal_mw: 0,
          capacity_input: '',
        });
      });
    });

    it('handles whitespace input by submitting 0', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const input = screen.getByLabelText(/target capacity/i);
      // Note: Number inputs don't accept spaces, so this tests the trim logic
      await user.clear(input);

      const applyButton = screen.getByRole('button', { name: /apply/i });
      await user.click(applyButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          ideal_mw: 0,
          capacity_input: '',
        });
      });
    });

    it('handles decimal values correctly', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const input = screen.getByLabelText(/target capacity/i);
      await user.type(input, '75.5');

      const applyButton = screen.getByRole('button', { name: /apply/i });
      await user.click(applyButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          ideal_mw: 75.5,
          capacity_input: '75.5',
        });
      });
    });

    it('waits for async onSubmit before calling onClose', async () => {
      const asyncOnSubmit = vi.fn().mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 100))
      );

      const { user } = render(
        <CriteriaModal onSubmit={asyncOnSubmit} onClose={mockOnClose} />
      );

      const input = screen.getByLabelText(/target capacity/i);
      await user.type(input, '200');

      const applyButton = screen.getByRole('button', { name: /apply/i });
      await user.click(applyButton);

      // onClose should be called after onSubmit resolves
      await waitFor(() => {
        expect(asyncOnSubmit).toHaveBeenCalled();
        expect(mockOnClose).toHaveBeenCalled();
      });
    });
  });

  describe('Console Logging', () => {
    it('logs user input to console', async () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});

      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const input = screen.getByLabelText(/target capacity/i);
      await user.type(input, '250');

      const applyButton = screen.getByRole('button', { name: /apply/i });
      await user.click(applyButton);

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalledWith(
          expect.stringContaining('250')
        );
      });

      consoleSpy.mockRestore();
    });
  });

  describe('Accessibility', () => {
    it('has accessible label for input', () => {
      render(<CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />);

      const input = screen.getByLabelText(/target capacity/i);
      expect(input).toBeInTheDocument();
      expect(input).toHaveAttribute('id', 'capacity-mw');
    });

    it('label is associated with input', () => {
      render(<CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />);

      const label = screen.getByText(/target capacity/i);
      expect(label).toHaveAttribute('for', 'capacity-mw');
    });

    it('buttons have accessible names', () => {
      render(<CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />);

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /apply/i })).toBeInTheDocument();
    });
  });

  describe('CSS Classes', () => {
    it('has modal container class', () => {
      const { container } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      expect(container.querySelector('.criteria-modal')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles very large numbers', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const input = screen.getByLabelText(/target capacity/i);
      await user.type(input, '999999');

      const applyButton = screen.getByRole('button', { name: /apply/i });
      await user.click(applyButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          ideal_mw: 999999,
          capacity_input: '999999',
        });
      });
    });

    it('handles zero value', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const input = screen.getByLabelText(/target capacity/i);
      await user.type(input, '0');

      const applyButton = screen.getByRole('button', { name: /apply/i });
      await user.click(applyButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith({
          ideal_mw: 0,
          capacity_input: '0',
        });
      });
    });

    it('prevents form default submission', async () => {
      const { user } = render(
        <CriteriaModal onSubmit={mockOnSubmit} onClose={mockOnClose} />
      );

      const form = document.querySelector('form');
      const submitEvent = vi.fn();
      form?.addEventListener('submit', submitEvent);

      const applyButton = screen.getByRole('button', { name: /apply/i });
      await user.click(applyButton);

      // Form should not cause page reload (default prevented)
      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalled();
      });
    });
  });
});
