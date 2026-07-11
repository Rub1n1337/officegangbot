import { Box, HStack } from '@chakra-ui/layout';
import {
  chakraComponents,
  ChakraStylesConfig,
  OptionBase,
  Props,
  Select,
  SelectComponent,
  SelectInstance,
} from 'chakra-react-select';
import { forwardRef, ReactNode } from 'react';
import { dark, light } from '@/theme/colors';
import { useColorModeValue } from '@chakra-ui/react';

const customComponents = {
  SingleValue: ({ children, ...props }: any) => {
    return (
      <chakraComponents.SingleValue {...props}>
        <HStack>
          {props.data.icon}
          <span>{children}</span>
        </HStack>
      </chakraComponents.SingleValue>
    );
  },
  Option: ({ children, ...props }: any) => {
    return (
      <chakraComponents.Option {...props}>
        <Box mr={2}>{props.data.icon}</Box> {children}
      </chakraComponents.Option>
    );
  },
};

const styles: ChakraStylesConfig<any, any, any> = {
  menuList: (provided) => ({
    ...provided,
    rounded: '14px',
    border: '1px solid',
    _light: {
      ...(provided as any)._light,
      shadow: light.shadow,
      borderColor: 'blackAlpha.200',
      bg: 'white',
    },
    _dark: {
      ...(provided as any)._dark,
      shadow: dark.shadow,
      borderColor: 'whiteAlpha.200',
      bg: 'navy.800',
    },
  }),
  placeholder: (provided) => ({
    ...provided,
    _light: {
      color: 'secondaryGray.700',
    },
    _dark: {
      color: 'secondaryGray.600',
    },
  }),
  dropdownIndicator: (provided) => ({
    ...provided,
    bg: 'transparent',
  }),
  groupHeading: (provided) => ({
    ...provided,
    _light: {
      bg: 'secondaryGray.100',
    },
    _dark: {
      bg: 'navy.800',
    },
  }),
  option: (provided, options) => ({
    ...provided,
    color: options.isSelected && 'white',
    _light: {
      bg: options.isSelected && light.brand,
      _hover: {
        bg: options.isSelected ? light.brand : 'white',
      },
    },
    _dark: {
      bg: options.isSelected && dark.brand,
      _hover: {
        bg: options.isSelected ? dark.brand : 'whiteAlpha.200',
      },
    },
  }),
  // Iris inset pill: the control sits on the card as a defined inset surface
  // with a 1px token border, accent on hover/focus.
  control: (provided, data) => ({
    ...provided,
    rounded: '12px',
    minH: '44px',
    _light: {
      borderColor: data.isFocused ? light.brand : 'blackAlpha.200',
      bg: 'secondaryGray.100',
      _hover: { borderColor: light.brand },
    },
    _dark: {
      borderColor: data.isFocused ? dark.brand : 'whiteAlpha.200',
      bg: 'navy.600',
      _hover: { borderColor: dark.brand },
    },
  }),
};

export type Option = OptionBase & {
  label: string;
  value: string;
  icon?: ReactNode;
};

export const SelectFieldBase = forwardRef<SelectInstance, Props>((props, ref) => {
  return (
    <Select<any, any, any>
      focusBorderColor={useColorModeValue(light.brand, dark.brand)}
      components={customComponents}
      chakraStyles={styles}
      ref={ref}
      {...props}
    />
  );
});

SelectFieldBase.displayName = 'SelectField';

export const SelectField = SelectFieldBase as SelectComponent;
