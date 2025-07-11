import { useFormContext } from "react-hook-form";
import { useId } from "react";

export function useFormField() {
  const { getFieldState, formState } = useFormContext();
  const id = useId();
  const name = id;

  const fieldState = getFieldState(name, formState);

  return {
    id,
    name,
    formItemId: `${id}-form-item`,
    formDescriptionId: `${id}-form-item-description`,
    formMessageId: `${id}-form-item-message`,
    ...fieldState,
  };
}
