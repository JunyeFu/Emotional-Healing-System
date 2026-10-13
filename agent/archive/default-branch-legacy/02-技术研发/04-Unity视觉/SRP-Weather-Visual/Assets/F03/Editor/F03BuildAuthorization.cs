using System;

namespace SRP.F03.Editor
{
    public static class F03BuildAuthorization
    {
        public const string EnvironmentVariable = "SRP_F03_DEV_BUILD_AUTHORIZED";

        public static bool IsAuthorized(string value) => string.Equals(value, "1", StringComparison.Ordinal);

        public static IDisposable Begin()
        {
            var previous = Environment.GetEnvironmentVariable(EnvironmentVariable);
            Environment.SetEnvironmentVariable(EnvironmentVariable, "1");
            return new RestoreEnvironment(previous);
        }

        private sealed class RestoreEnvironment : IDisposable
        {
            private readonly string previous;
            private bool disposed;

            public RestoreEnvironment(string previousValue) => previous = previousValue;

            public void Dispose()
            {
                if (disposed)
                {
                    return;
                }
                Environment.SetEnvironmentVariable(EnvironmentVariable, previous);
                disposed = true;
            }
        }
    }
}
