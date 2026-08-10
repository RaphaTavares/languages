# Top 20 React.js Interview Questions

## 1. What is React and what are its key features?

React is an open-source JavaScript library developed by Meta for building user interfaces, particularly single-page applications. Key features:

- **Component-based architecture** — reusable, isolated UI pieces
- **Virtual DOM** — efficient diffing and updates
- **Declarative** — describe what the UI should look like for a given state
- **Unidirectional data flow** — predictable state management
- **JSX** — HTML-like syntax in JavaScript
- **Hooks** — state and lifecycle in function components

## 2. What is the Virtual DOM and how does it work?

The Virtual DOM is an in-memory representation of the real DOM. When state changes, React:

1. Creates a new Virtual DOM tree.
2. Diffs it against the previous Virtual DOM (reconciliation).
3. Computes the minimum set of changes needed.
4. Applies only those changes to the real DOM in a batch.

This avoids expensive full-DOM re-renders and makes updates efficient.

## 3. What is JSX?

JSX (JavaScript XML) is a syntax extension that lets you write HTML-like markup inside JavaScript. It gets transpiled (by Babel) into `React.createElement()` calls.

```jsx
const element = <h1 className="title">Hello, {name}</h1>;
// Compiles to:
// React.createElement('h1', { className: 'title' }, 'Hello, ', name);
```

JSX is not required but makes React code more readable.

## 4. What is the difference between functional and class components?

- **Class components** — ES6 classes extending `React.Component`, use `this.state`, lifecycle methods (`componentDidMount`, etc.), and `this.props`.
- **Functional components** — plain functions that receive props and return JSX. With Hooks, they can manage state and side effects.

Modern React favors functional components with Hooks; class components are considered legacy.

```jsx
// Functional
function Greeting({ name }) {
  return <h1>Hello, {name}</h1>;
}

// Class
class Greeting extends React.Component {
  render() {
    return <h1>Hello, {this.props.name}</h1>;
  }
}
```

## 5. What are props and state? How do they differ?

- **Props** — read-only inputs passed from parent to child. Immutable within the component.
- **State** — internal, mutable data managed by the component itself. Changes trigger re-renders.

Rule of thumb: props flow down, state stays local (or lifted up when shared).

## 6. What is the `useState` Hook?

`useState` lets functional components hold local state. It returns a stateful value and a setter function.

```jsx
const [count, setCount] = useState(0);

return <button onClick={() => setCount(count + 1)}>{count}</button>;
```

Calling the setter triggers a re-render. Use the functional form (`setCount(c => c + 1)`) when the new state depends on the previous one.

## 7. What is the `useEffect` Hook and when does it run?

`useEffect` handles side effects (data fetching, subscriptions, DOM manipulation) in functional components.

```jsx
useEffect(() => {
  const sub = subscribe();
  return () => sub.unsubscribe(); // cleanup
}, [dependency]);
```

- **No dependency array** — runs after every render.
- **Empty array `[]`** — runs once after mount.
- **`[deps]`** — runs when any dep changes.
- **Return function** — cleanup, runs before next effect and on unmount.

## 8. What are the rules of Hooks?

1. **Only call Hooks at the top level** — never inside loops, conditions, or nested functions.
2. **Only call Hooks from React functions** — components or custom Hooks, not regular JS functions.

These rules ensure Hooks are called in the same order on every render, which is how React associates state with each Hook.

## 9. What is the Context API and when should you use it?

Context provides a way to pass data through the component tree without prop drilling.

```jsx
const ThemeContext = createContext('light');

function App() {
  return (
    <ThemeContext.Provider value="dark">
      <Toolbar />
    </ThemeContext.Provider>
  );
}

function Toolbar() {
  const theme = useContext(ThemeContext);
  return <div className={theme}>...</div>;
}
```

Use for **global-ish, low-frequency data** (theme, user, locale). For heavy state, prefer a state manager (Redux, Zustand) to avoid unnecessary re-renders.

## 10. What is the difference between controlled and uncontrolled components?

- **Controlled** — form state is managed by React via `value` and `onChange`.
- **Uncontrolled** — form state lives in the DOM; accessed via `ref`.

```jsx
// Controlled
<input value={name} onChange={(e) => setName(e.target.value)} />

// Uncontrolled
<input ref={inputRef} defaultValue="foo" />
```

Controlled is the recommended default; uncontrolled is useful for integrating with non-React code or file inputs.

## 11. What are keys in React and why are they important?

Keys are special string attributes that help React identify which items in a list have changed, been added, or removed. They should be **stable, unique, and predictable**.

```jsx
{items.map((item) => <li key={item.id}>{item.name}</li>)}
```

Avoid using array **indexes** as keys when the list can reorder — it causes bugs with local component state and can hurt performance.

## 12. What is reconciliation in React?

Reconciliation is the algorithm React uses to diff two Virtual DOM trees and figure out what to update. Key heuristics:

- Elements of **different types** produce different trees (React unmounts the old one entirely).
- Elements of the **same type** are updated in place (React updates only changed attributes).
- **Keys** help match children across renders.

This makes the diff O(n) instead of O(n³).

## 13. What are `useMemo` and `useCallback`?

Both memoize values to avoid unnecessary recomputation or re-renders.

- **`useMemo`** — memoizes a computed value.
  ```jsx
  const expensive = useMemo(() => computeHeavy(data), [data]);
  ```
- **`useCallback`** — memoizes a function reference.
  ```jsx
  const handleClick = useCallback(() => doSomething(id), [id]);
  ```

Use sparingly — they add complexity and their own overhead. Only reach for them when profiling shows a real cost.

## 14. What is `React.memo`?

`React.memo` is a higher-order component that memoizes a functional component, skipping re-renders when its props haven't changed (shallow comparison by default).

```jsx
const MyComponent = React.memo(function MyComponent({ value }) {
  return <div>{value}</div>;
});
```

Best paired with `useCallback`/`useMemo` on props to keep references stable.

## 15. What are the component lifecycle phases and their Hook equivalents?

Class component lifecycle → Hook equivalent:

- **Mounting**: `constructor`, `componentDidMount` → `useState`, `useEffect(() => {...}, [])`
- **Updating**: `componentDidUpdate` → `useEffect(() => {...}, [deps])`
- **Unmounting**: `componentWillUnmount` → cleanup function returned from `useEffect`
- **Error handling**: `componentDidCatch`, `getDerivedStateFromError` → still class-only (Error Boundaries)

## 16. What are Error Boundaries?

Error Boundaries are class components that catch JavaScript errors in their child component tree during rendering, in lifecycle methods, and in constructors. They log errors and display a fallback UI.

```jsx
class ErrorBoundary extends React.Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    logToService(error, info);
  }

  render() {
    if (this.state.hasError) return <h1>Something went wrong.</h1>;
    return this.props.children;
  }
}
```

They don't catch errors in event handlers, async code, or SSR.

## 17. What is prop drilling and how do you avoid it?

Prop drilling is passing props through multiple intermediate components that don't use them, just to reach a deeply nested one.

Ways to avoid it:

- **Context API** — for cross-cutting concerns (theme, auth).
- **State management libraries** — Redux, Zustand, Jotai, Recoil.
- **Component composition** — pass components as children/props instead of data.

## 18. What is the difference between `useEffect` and `useLayoutEffect`?

- **`useEffect`** — runs **asynchronously** after the browser paints. Doesn't block visual updates. Default choice.
- **`useLayoutEffect`** — runs **synchronously** after DOM mutations but before the browser paints. Use when you need to measure DOM or make DOM changes that must be visible in the same paint (avoids flicker).

## 19. What are custom Hooks?

Custom Hooks are JavaScript functions whose names start with `use` and that may call other Hooks. They let you extract and reuse stateful logic across components.

```jsx
function useFetch(url) {
  const [data, setData] = useState(null);
  useEffect(() => {
    fetch(url).then((r) => r.json()).then(setData);
  }, [url]);
  return data;
}

// Usage
const user = useFetch('/api/user');
```

Each call to a custom Hook gets its own isolated state.

## 20. What is the difference between server-side rendering (SSR), client-side rendering (CSR), and static site generation (SSG)?

- **CSR** — the browser downloads a minimal HTML shell and JS bundle; React renders the UI on the client. Fast navigation after load, but slower initial paint and worse SEO.
- **SSR** — the server renders HTML on each request and sends it fully populated. Better initial paint and SEO, higher server cost. React hydrates the HTML on the client.
- **SSG** — HTML is pre-rendered at build time and served as static files. Fastest, cheapest, but only works when content doesn't change per request.

Frameworks like **Next.js** and **Remix** support all three (often per-route).

## 21. What is React Router and how does it work?

React Router is the standard client-side routing library for React SPAs. It maps URLs to components and manages navigation without full page reloads.

```jsx
import { createBrowserRouter, RouterProvider, Link, Outlet } from 'react-router-dom';

const router = createBrowserRouter([
  { path: '/', element: <Layout />, children: [
    { index: true, element: <Home /> },
    { path: 'users/:id', element: <User />, loader: userLoader },
  ]},
]);

<RouterProvider router={router} />
```

Key concepts: **nested routes** with `<Outlet />`, **dynamic params** (`useParams`), **programmatic navigation** (`useNavigate`), **loaders/actions** (v6.4+ data APIs). Alternatives: **TanStack Router** (type-safe), **Next.js file-based routing**.

## 22. What is Redux? Explain store, actions, reducers, and middleware.

Redux is a predictable state container based on a unidirectional data flow:

- **Store** — a single source of truth (one object).
- **Action** — a plain object describing what happened: `{ type: 'user/login', payload: {...} }`.
- **Reducer** — a pure function `(state, action) => newState`.
- **Middleware** — intercepts actions (logging, async, side effects). Examples: `redux-thunk`, `redux-saga`, RTK's `listenerMiddleware`.

```jsx
const store = createStore(rootReducer, applyMiddleware(thunk));
store.dispatch({ type: 'counter/increment' });
```

Access state via `useSelector` and dispatch via `useDispatch` (React-Redux hooks).

## 23. What is Redux Toolkit and why prefer it over classic Redux?

Redux Toolkit (RTK) is the official, opinionated Redux — massively less boilerplate.

```jsx
const counterSlice = createSlice({
  name: 'counter',
  initialState: { value: 0 },
  reducers: {
    increment: (state) => { state.value += 1; },   // Immer allows "mutation"
  },
});

export const { increment } = counterSlice.actions;
export const store = configureStore({ reducer: { counter: counterSlice.reducer } });
```

Wins: `createSlice` (auto-generated action creators), `configureStore` (built-in DevTools + middleware), `createAsyncThunk` for async, **RTK Query** for data fetching / caching (often replaces the need for a separate library).

## 24. What is React Query / SWR — server state vs client state?

**Server state** (data fetched from an API) has different needs than **client/UI state** (modal open, form draft):

- Server state is **remote**, **async**, **can go stale**, and needs **caching, revalidation, and deduplication**.
- Client state is local, synchronous, and cheap.

**TanStack Query (React Query)** and **SWR** handle server state:

```jsx
const { data, isLoading, error } = useQuery({
  queryKey: ['user', id],
  queryFn: () => fetchUser(id),
  staleTime: 60_000,
});
```

Features: automatic caching keyed by input, background refetch on focus/reconnect, request deduplication, optimistic updates, pagination/infinite scroll. **Rule of thumb: don't put server data in Redux/Context — use a data-fetching library.**

## 25. What is `useRef` and when should you use it?

`useRef` returns a mutable object (`{ current: value }`) that **persists across renders** and does **not trigger re-renders** when changed.

Two main uses:
- **DOM refs** — access an element imperatively (focus, scroll, measurements).
- **Instance-like values** — timer IDs, previous values, subscription handles.

```jsx
const inputRef = useRef(null);
useEffect(() => { inputRef.current.focus(); }, []);

const renderCount = useRef(0);
renderCount.current += 1;   // no re-render
```

If updating a value should trigger a re-render, use `useState` instead.

## 26. What are `forwardRef` and `useImperativeHandle`?

**`forwardRef`** lets a parent attach a `ref` to a child component's inner DOM element (or an imperative API).

```jsx
const FancyInput = forwardRef((props, ref) => <input ref={ref} {...props} />);

// Parent:
const ref = useRef(null);
<FancyInput ref={ref} />;
```

**`useImperativeHandle`** customizes what the ref exposes, avoiding leaking the full DOM node:

```jsx
const Modal = forwardRef((props, ref) => {
  useImperativeHandle(ref, () => ({ open, close }), []);
  ...
});
```

Note: in **React 19**, `ref` is passed as a normal prop and `forwardRef` is no longer needed for function components.

## 27. What is `useReducer` and when should you prefer it over `useState`?

`useReducer` manages state via a reducer function, similar to Redux but local to a component.

```jsx
const [state, dispatch] = useReducer(reducer, initialState);
dispatch({ type: 'ADD', payload: item });
```

Prefer it when:
- State has **multiple sub-values** that update together.
- **Next state depends on complex logic** across several actions.
- You want to **test state transitions** as a pure function.
- Actions are dispatched from **many places** and you want a single update site.

For simple boolean/counter/string state, `useState` is fine.

## 28. What are Portals and when are they useful?

Portals render a child into a **different DOM subtree** than the parent, while keeping React tree semantics (events bubble through the React parent).

```jsx
createPortal(<Modal />, document.getElementById('modal-root'));
```

Use cases: modals, tooltips, popovers — where you need to escape parent overflow/z-index/stacking contexts without breaking event flow or context.

## 29. What is code splitting and how do `React.lazy` + `Suspense` help?

Code splitting breaks the bundle into chunks loaded on demand instead of one large file. `React.lazy` loads a component only when rendered; `Suspense` shows a fallback while it loads.

```jsx
const Settings = React.lazy(() => import('./Settings'));

<Suspense fallback={<Spinner />}>
  <Settings />
</Suspense>
```

Combine with route-level splitting for best results. Bundlers (Vite, webpack) handle the dynamic import automatically.

## 30. What are React Server Components (RSC)?

Server Components (stable in React 19, popularized by Next.js App Router) run **on the server**, producing a serialized description of the UI. They:

- Can access DBs, filesystem, secrets directly.
- **Don't ship JS to the client** (smaller bundles).
- Can't use state or effects (`useState`, `useEffect`) or browser APIs.
- Can import Client Components (marked with `'use client'`).

Client Components handle interactivity; Server Components handle data-heavy, non-interactive UI. They can be freely composed, moving work to the server where it belongs.

## 31. What is hydration and what causes hydration errors?

**Hydration** is the process where React attaches event listeners and state to server-rendered HTML on the client, "reviving" it into an interactive app.

Hydration **fails** when the server-rendered HTML doesn't match what the client renders on the first pass. Common causes:
- Using `Date.now()`, `Math.random()`, `typeof window`, or reading `localStorage` in initial render.
- Different content based on browser locale/timezone/user agent.
- Invalid HTML nesting (`<p><div/></p>`).

Fixes: render the varying content only after mount (`useEffect` + state), or use `suppressHydrationWarning` for known-safe mismatches (last resort).

## 32. What are HOCs and Render Props?

Pre-Hooks patterns for sharing behavior:

- **HOC (Higher-Order Component)** — a function that takes a component and returns a wrapped one.
  ```jsx
  const withAuth = (Cmp) => (props) => user ? <Cmp {...props} /> : <Login />;
  ```
- **Render prop** — a component whose child is a function receiving state.
  ```jsx
  <Mouse>{({ x, y }) => <div>{x},{y}</div>}</Mouse>
  ```

Both are **still valid** but Hooks handle most of the same use cases with less nesting and cleaner composition. Encounter mostly in older codebases and some libraries (e.g., Formik's render props).

## 33. What is React Strict Mode?

`<StrictMode>` is a dev-only wrapper that helps catch problems by:

- **Double-invoking** function components, `useState` initializers, and effects (mount → unmount → mount) to surface impure logic and missing cleanup.
- Warning on deprecated APIs and unsafe lifecycles.
- Detecting unexpected side effects.

No effect in production. Wrap your app root with it — if your code breaks, the code was already buggy.

## 34. What are Concurrent Features (`useTransition`, `useDeferredValue`)?

Concurrent React can **interrupt and prioritize** renders instead of blocking on them.

- **`useTransition`** — mark a state update as non-urgent so React can keep the UI responsive.
  ```jsx
  const [isPending, startTransition] = useTransition();
  startTransition(() => setFilter(input));   // low-priority
  ```
- **`useDeferredValue`** — defer a value so an expensive derived render doesn't block urgent updates.
  ```jsx
  const deferredQuery = useDeferredValue(query);
  ```

Use for expensive lists, filtering, or search-as-you-type without freezing the input.

## 35. How do you test React components?

**React Testing Library (RTL)** + **Vitest / Jest** is the mainstream stack. Philosophy: test behavior from the user's perspective, not implementation details.

```jsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('increments on click', async () => {
  render(<Counter />);
  await userEvent.click(screen.getByRole('button', { name: /add/i }));
  expect(screen.getByText('Count: 1')).toBeInTheDocument();
});
```

Prefer accessible queries: `getByRole`, `getByLabelText`, `getByText`. Avoid snapshots for anything non-trivial. Mock network with **MSW**. Use **Playwright** for cross-browser E2E.

## 36. What are the main React performance optimization techniques?

- **Profile first** with React DevTools Profiler; don't optimize blindly.
- **Memoize** with `React.memo`, `useMemo`, `useCallback` for components/values that are actually expensive and receive stable props.
- **Virtualize** long lists with `react-window` / `react-virtual`.
- **Code split** with `React.lazy` + route-based chunks.
- Split state — colocated state changes re-render only its owners; context re-renders every consumer.
- Use **`useTransition`** for non-urgent updates.
- Avoid unnecessary re-renders by keeping object/array/function references stable.
- Debounce/throttle expensive handlers.
- SSR/SSG for faster first paint.

## 37. What is `Fragment` and when to use it?

`Fragment` (`<>...</>` shorthand or `<React.Fragment>`) lets a component return multiple children without adding an extra DOM node.

```jsx
return (
  <>
    <td>Name</td>
    <td>Age</td>
  </>
);
```

Use the long form (`<Fragment key={id}>`) when a fragment needs a key (mapping over lists of pairs).

## 38. What are React accessibility (a11y) best practices?

- Use **semantic HTML** — `<button>`, not `<div onClick>`; `<nav>`, `<main>`, `<h1>`. Correct heading order.
- **Label form inputs** with `<label htmlFor>` or `aria-label`.
- Manage **focus** — after route changes, opening modals, or dynamic content updates.
- Use **`role`** and **ARIA** attributes only when semantic HTML isn't enough.
- Test with a **keyboard only** (Tab, Enter, Escape). Check focus rings — don't disable them.
- Use tools: **eslint-plugin-jsx-a11y**, **axe-core**, Lighthouse.
- Support prefers-reduced-motion, sufficient color contrast, and screen-reader-only text (`sr-only`).

## 39. How do you handle forms in React?

**Small forms** — controlled inputs with `useState`.

**Complex forms** — use a library:
- **React Hook Form** — uncontrolled + refs, minimal re-renders, small bundle, integrates with schema validators.
- **Formik** — older, more re-renders, still popular.
- **TanStack Form** — newer, headless.

```jsx
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

const schema = z.object({ email: z.string().email() });

const { register, handleSubmit, formState: { errors } } = useForm({
  resolver: zodResolver(schema),
});

<form onSubmit={handleSubmit(onSubmit)}>
  <input {...register('email')} />
  {errors.email && <span>{errors.email.message}</span>}
</form>
```

Pair the resolver with a schema library (`zod`, `yup`) for shared client/server validation.

## 40. What is `useSyncExternalStore` and why does it exist?

`useSyncExternalStore` (React 18+) lets components safely subscribe to **external stores** (Redux, Zustand, browser APIs, custom event sources) without tearing in Concurrent Mode.

```jsx
function useOnlineStatus() {
  return useSyncExternalStore(
    (cb) => {
      window.addEventListener('online', cb);
      window.addEventListener('offline', cb);
      return () => { window.removeEventListener('online', cb); window.removeEventListener('offline', cb); };
    },
    () => navigator.onLine,        // client snapshot
    () => true                     // server snapshot (SSR)
  );
}
```

Library authors use it under the hood — you rarely call it directly. Guarantees a consistent read across a render, avoiding stale/torn state that older subscription patterns could produce.
