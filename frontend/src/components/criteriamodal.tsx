import { FormEvent, useState } from "react";

type CriteriaFormPayload = {
  ideal_mw: number;
  capacity_input: string;
};

type CriteriaModalProps = {
  onSubmit: (payload: CriteriaFormPayload) => Promise<void> | void;
  onClose: () => void;
};

const CriteriaModal = ({ onSubmit, onClose }: CriteriaModalProps) => {
  const [capacityInput, setCapacityInput] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedInput = capacityInput.trim();
    const parsedCapacity = Number.parseFloat(trimmedInput);
    const idealMw = Number.isFinite(parsedCapacity) ? parsedCapacity : 0;

    console.log(
      `[CriteriaModal] User entered capacity: ${
        trimmedInput || "0"
      } MW | Posting ideal_mw payload: ${idealMw} MW`
    );

    await onSubmit({
      ideal_mw: idealMw,
      capacity_input: trimmedInput,
    });

    onClose();
  };

  return (
    <div className="criteria-modal">
      <form onSubmit={handleSubmit}>
        <label htmlFor="capacity-mw" className="block text-sm font-medium text-gray-700">
          Target Capacity (MW)
        </label>
        <input
          id="capacity-mw"
          type="number"
          inputMode="decimal"
          min="0"
          step="0.1"
          value={capacityInput}
          onChange={(event) => setCapacityInput(event.target.value)}
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
        />

        <div className="mt-4 flex justify-end space-x-3">
          <button
            type="button"
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="inline-flex justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700"
          >
            Apply
          </button>
        </div>
      </form>
    </div>
  );
};

export default CriteriaModal;
