type Props = {
  label: string;
  valueLabel: string;
  onMinus: () => void;
  onPlus: () => void;
  minusDisabled?: boolean;
  plusDisabled?: boolean;
};

export function TouchStepper({
  label,
  valueLabel,
  onMinus,
  onPlus,
  minusDisabled,
  plusDisabled,
}: Props) {
  return (
    <div className="touch-stepper">
      <span className="touch-stepper-label">{label}</span>
      <div className="touch-stepper-row">
        <button
          type="button"
          className="touch-stepper-btn"
          aria-label={`Menos ${label}`}
          disabled={minusDisabled}
          onClick={onMinus}
        >
          −
        </button>
        <span className="touch-stepper-value">{valueLabel}</span>
        <button
          type="button"
          className="touch-stepper-btn"
          aria-label={`Más ${label}`}
          disabled={plusDisabled}
          onClick={onPlus}
        >
          +
        </button>
      </div>
    </div>
  );
}
