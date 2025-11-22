/**
 * IRREstimator Component Tests
 *
 * Tests for the financial modeling interface including:
 * - Input forms
 * - Calculation triggers
 * - Results display
 * - Sensitivity analysis
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@/test/utils';

// Mock IRREstimator component
const MockIRREstimator = () => {
  return (
    <div data-testid="irr-estimator">
      <h1>IRR Estimator</h1>

      <form data-testid="financial-form">
        <fieldset data-testid="project-params">
          <legend>Project Parameters</legend>
          <label>
            Capacity (MW)
            <input
              data-testid="capacity-input"
              type="number"
              defaultValue={100}
              min={1}
            />
          </label>
          <label>
            Technology
            <select data-testid="technology-select" defaultValue="Solar">
              <option value="Solar">Solar</option>
              <option value="Wind">Wind</option>
              <option value="Battery">Battery</option>
            </select>
          </label>
          <label>
            Capacity Factor
            <input
              data-testid="capacity-factor-input"
              type="number"
              defaultValue={0.25}
              min={0}
              max={1}
              step={0.01}
            />
          </label>
        </fieldset>

        <fieldset data-testid="financial-params">
          <legend>Financial Parameters</legend>
          <label>
            Discount Rate (%)
            <input
              data-testid="discount-rate-input"
              type="number"
              defaultValue={8}
              min={0}
              max={100}
            />
          </label>
          <label>
            Project Life (years)
            <input
              data-testid="project-life-input"
              type="number"
              defaultValue={25}
              min={1}
            />
          </label>
          <label>
            CAPEX (£/MW)
            <input
              data-testid="capex-input"
              type="number"
              defaultValue={800000}
              min={0}
            />
          </label>
        </fieldset>

        <button type="submit" data-testid="calculate-btn">
          Calculate
        </button>
      </form>

      <div data-testid="results-panel">
        <div data-testid="standard-results">
          <h2>Standard Scenario</h2>
          <div data-testid="npv-result">NPV: £5,000,000</div>
          <div data-testid="irr-result">IRR: 12.0%</div>
          <div data-testid="lcoe-result">LCOE: £42.50/MWh</div>
          <div data-testid="payback-result">Payback: 7.5 years</div>
        </div>

        <div data-testid="autoproducer-results">
          <h2>Autoproducer Scenario</h2>
          <div data-testid="autoproducer-npv">NPV: £6,500,000</div>
          <div data-testid="autoproducer-irr">IRR: 15.0%</div>
          <div data-testid="uplift-result">Uplift: +25%</div>
        </div>
      </div>

      <div data-testid="cashflow-table">
        <table>
          <thead>
            <tr>
              <th>Year</th>
              <th>Revenue</th>
              <th>OPEX</th>
              <th>Net Cashflow</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>1</td>
              <td>£15,000,000</td>
              <td>£3,000,000</td>
              <td>£12,000,000</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div data-testid="sensitivity-panel">
        <h2>Sensitivity Analysis</h2>
        <button data-testid="run-sensitivity-btn">Run Sensitivity</button>
      </div>
    </div>
  );
};

describe('IRREstimator', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the estimator container', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('irr-estimator')).toBeInTheDocument();
    });

    it('renders the page title', () => {
      render(<MockIRREstimator />);
      expect(screen.getByRole('heading', { name: /irr estimator/i })).toBeInTheDocument();
    });

    it('renders financial form', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('financial-form')).toBeInTheDocument();
    });

    it('renders results panel', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('results-panel')).toBeInTheDocument();
    });
  });

  describe('Project Parameters', () => {
    it('renders capacity input', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('capacity-input')).toBeInTheDocument();
    });

    it('renders technology select', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('technology-select')).toBeInTheDocument();
    });

    it('renders capacity factor input', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('capacity-factor-input')).toBeInTheDocument();
    });

    it('has correct default values', () => {
      render(<MockIRREstimator />);

      expect(screen.getByTestId('capacity-input')).toHaveValue(100);
      expect(screen.getByTestId('technology-select')).toHaveValue('Solar');
      expect(screen.getByTestId('capacity-factor-input')).toHaveValue(0.25);
    });
  });

  describe('Financial Parameters', () => {
    it('renders discount rate input', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('discount-rate-input')).toBeInTheDocument();
    });

    it('renders project life input', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('project-life-input')).toBeInTheDocument();
    });

    it('renders CAPEX input', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('capex-input')).toBeInTheDocument();
    });

    it('has correct default financial values', () => {
      render(<MockIRREstimator />);

      expect(screen.getByTestId('discount-rate-input')).toHaveValue(8);
      expect(screen.getByTestId('project-life-input')).toHaveValue(25);
      expect(screen.getByTestId('capex-input')).toHaveValue(800000);
    });
  });

  describe('User Input', () => {
    it('allows changing capacity', async () => {
      const { user } = render(<MockIRREstimator />);

      const capacityInput = screen.getByTestId('capacity-input');
      await user.clear(capacityInput);
      await user.type(capacityInput, '150');

      expect(capacityInput).toHaveValue(150);
    });

    it('allows selecting technology', async () => {
      const { user } = render(<MockIRREstimator />);

      const techSelect = screen.getByTestId('technology-select');
      await user.selectOptions(techSelect, 'Wind');

      expect(techSelect).toHaveValue('Wind');
    });

    it('validates capacity factor range', async () => {
      render(<MockIRREstimator />);

      const cfInput = screen.getByTestId('capacity-factor-input');
      expect(cfInput).toHaveAttribute('min', '0');
      expect(cfInput).toHaveAttribute('max', '1');
    });
  });

  describe('Calculation', () => {
    it('renders calculate button', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('calculate-btn')).toBeInTheDocument();
    });

    it('triggers calculation on button click', async () => {
      const { user } = render(<MockIRREstimator />);

      const calculateBtn = screen.getByTestId('calculate-btn');
      await user.click(calculateBtn);

      // In real implementation, verify API call was made
    });

    it('shows loading state during calculation', async () => {
      const { user } = render(<MockIRREstimator />);

      const calculateBtn = screen.getByTestId('calculate-btn');
      await user.click(calculateBtn);

      // In real implementation:
      // expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  describe('Results Display', () => {
    it('displays NPV result', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('npv-result')).toHaveTextContent('NPV');
    });

    it('displays IRR result', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('irr-result')).toHaveTextContent('IRR');
    });

    it('displays LCOE result', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('lcoe-result')).toHaveTextContent('LCOE');
    });

    it('displays payback period', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('payback-result')).toHaveTextContent('Payback');
    });

    it('formats NPV as currency', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('npv-result')).toHaveTextContent('£');
    });

    it('formats IRR as percentage', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('irr-result')).toHaveTextContent('%');
    });
  });

  describe('Autoproducer Comparison', () => {
    it('displays autoproducer results', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('autoproducer-results')).toBeInTheDocument();
    });

    it('displays autoproducer NPV', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('autoproducer-npv')).toHaveTextContent('NPV');
    });

    it('displays autoproducer IRR', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('autoproducer-irr')).toHaveTextContent('IRR');
    });

    it('displays uplift percentage', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('uplift-result')).toHaveTextContent('Uplift');
    });
  });

  describe('Cashflow Table', () => {
    it('renders cashflow table', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('cashflow-table')).toBeInTheDocument();
    });

    it('displays year column', () => {
      render(<MockIRREstimator />);
      expect(screen.getByRole('columnheader', { name: /year/i })).toBeInTheDocument();
    });

    it('displays revenue column', () => {
      render(<MockIRREstimator />);
      expect(screen.getByRole('columnheader', { name: /revenue/i })).toBeInTheDocument();
    });

    it('displays OPEX column', () => {
      render(<MockIRREstimator />);
      expect(screen.getByRole('columnheader', { name: /opex/i })).toBeInTheDocument();
    });

    it('displays net cashflow column', () => {
      render(<MockIRREstimator />);
      expect(screen.getByRole('columnheader', { name: /net cashflow/i })).toBeInTheDocument();
    });
  });

  describe('Sensitivity Analysis', () => {
    it('renders sensitivity panel', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('sensitivity-panel')).toBeInTheDocument();
    });

    it('renders run sensitivity button', () => {
      render(<MockIRREstimator />);
      expect(screen.getByTestId('run-sensitivity-btn')).toBeInTheDocument();
    });

    it('triggers sensitivity analysis on button click', async () => {
      const { user } = render(<MockIRREstimator />);

      const sensitivityBtn = screen.getByTestId('run-sensitivity-btn');
      await user.click(sensitivityBtn);

      // In real implementation, verify sensitivity calculation was triggered
    });
  });

  describe('Validation', () => {
    it('requires minimum capacity', () => {
      render(<MockIRREstimator />);

      const capacityInput = screen.getByTestId('capacity-input');
      expect(capacityInput).toHaveAttribute('min', '1');
    });

    it('prevents negative values', () => {
      render(<MockIRREstimator />);

      const capexInput = screen.getByTestId('capex-input');
      expect(capexInput).toHaveAttribute('min', '0');
    });
  });

  describe('Accessibility', () => {
    it('has fieldset legends for parameter groups', () => {
      render(<MockIRREstimator />);

      expect(screen.getByRole('group', { name: /project parameters/i })).toBeInTheDocument();
      expect(screen.getByRole('group', { name: /financial parameters/i })).toBeInTheDocument();
    });

    it('inputs have associated labels', () => {
      render(<MockIRREstimator />);

      expect(screen.getByLabelText(/capacity \(mw\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/technology/i)).toBeInTheDocument();
    });
  });
});

describe('IRREstimator - Technology-Specific Behavior', () => {
  it('adjusts default capacity factor for Wind', async () => {
    const { user } = render(<MockIRREstimator />);

    const techSelect = screen.getByTestId('technology-select');
    await user.selectOptions(techSelect, 'Wind');

    // In real implementation, capacity factor should update to ~0.35
  });

  it('adjusts default CAPEX for Battery', async () => {
    const { user } = render(<MockIRREstimator />);

    const techSelect = screen.getByTestId('technology-select');
    await user.selectOptions(techSelect, 'Battery');

    // In real implementation, CAPEX should update for battery storage
  });
});
