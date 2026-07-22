import {
  FormControl,
  FormControlProps,
  FormErrorMessage,
  FormLabel,
} from '@chakra-ui/form-control';
import { Flex, Spacer, Text } from '@chakra-ui/layout';
import { chakra, Icon, Tooltip } from '@chakra-ui/react';
import { MdInfoOutline } from 'react-icons/md';
import { ReactNode } from 'react';
import {
  Controller,
  ControllerProps,
  FieldValues,
  Path,
  UseControllerProps,
} from 'react-hook-form';

export function Form(props: FormControlProps) {
  return (
    <FormControl
      as={Flex}
      direction="column"
      bg="CardBackground"
      rounded="16px"
      p={5}
      boxShadow="normal"
      borderWidth="1px"
      borderColor="CardBorder"
      transition="border-color .15s ease"
      _hover={{ borderColor: 'brand.400' }}
      {...props}
    >
      {props.children}
    </FormControl>
  );
}

export type FormCardProps = {
  required?: boolean;
  baseControl?: FormControlProps;
  /**
   * Show an error message if not null
   */
  error?: string;
  label?: string | ReactNode;
  description?: string | ReactNode;
  /** Optional extra help shown in a tooltip on an info icon next to the label —
   * for fields that need a longer explanation than the description (e.g. how to
   * copy a Message ID). Hover on desktop, focus/tap on mobile. */
  tooltip?: string | ReactNode;

  children: ReactNode;
};

export function FormCard({
  label,
  description,
  tooltip,
  required,
  baseControl,
  children,
  error,
}: FormCardProps) {
  return (
    <Form isRequired={required} isInvalid={error != null} {...baseControl}>
      <Flex align="center" gap={1.5}>
        <FormLabel fontSize="15px" fontWeight="600" mb={0}>
          {label}
        </FormLabel>
        {tooltip != null && (
          <Tooltip
            label={tooltip}
            hasArrow
            placement="top"
            rounded="md"
            fontSize="xs"
            p={2.5}
            maxW="280px"
            openDelay={150}
          >
            <chakra.span
              tabIndex={0}
              display="inline-flex"
              cursor="help"
              color="TextSecondary"
              aria-label="More information"
              _hover={{ color: 'Brand' }}
              _focusVisible={{ color: 'Brand', outline: 'none' }}
            >
              <Icon as={MdInfoOutline} boxSize="15px" />
            </chakra.span>
          </Tooltip>
        )}
      </Flex>
      <Text fontSize="13px" color="TextSecondary">
        {description}
      </Text>
      <Spacer mt={2} />
      {children}
      <FormErrorMessage>{error}</FormErrorMessage>
    </Form>
  );
}

export type FormCardControllerProps<
  TFieldValue extends FieldValues,
  TName extends Path<TFieldValue>
> = {
  control: Omit<FormCardProps, 'error' | 'children'>;
  controller: UseControllerProps<TFieldValue, TName>;
  render: ControllerProps<TFieldValue, TName>['render'];
};

export function FormCardController<
  TFieldValue extends FieldValues,
  TName extends Path<TFieldValue>
>({ control, controller, render }: FormCardControllerProps<TFieldValue, TName>) {
  return (
    <Controller
      {...controller}
      render={(props) => (
        <FormCard {...control} error={props.fieldState.error?.message}>
          {render(props)}
        </FormCard>
      )}
    />
  );
}
